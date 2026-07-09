#!/usr/bin/env python3
"""
Tick-level backtester for the Wayward EA, engineered to approximate the MT5
Strategy Tester ("Every tick" on real bid/ask ticks).

Fidelity notes
--------------
* Bars are built from BID prices (MT5 default chart), on the working timeframe.
* Bollinger / RSI / ATR are recomputed on the FORMING bar (index 0) every tick,
  exactly as the EA reads them:
    - Bollinger  = SMA(close,P) +/- dev * populationStdDev(close,P)
    - RSI        = Wilder's SMMA smoothing (seeded by SMA of first P changes)
    - ATR        = Wilder's smoothing of True Range (seeded by SMA of first P TRs)
  Completed-bar recursion state is carried forward; the forming bar's close is
  the running bid, its high/low are the running bid high/low.
* STOP orders fill when ask (buy) / bid (sell) crosses the level; gap fills take
  the crossing price (adverse). SL fills at market (worse of SL / market); TP
  fills at the target level.
* One position OR one pending order at a time (as the EA enforces).
* Lots sized from risk over the ATR stop distance, clamped to broker limits.
"""

import sys, glob, time, argparse
import numpy as np
import pandas as pd
from numba import njit

# -----------------------------------------------------------------------------
# Parameters (mirror the EA inputs; spread cap adapted for the instrument)
# -----------------------------------------------------------------------------
P = dict(
    tf_minutes      = 5,
    bb_period       = 20,
    bb_dev          = 2.0,
    rsi_period      = 14,
    rsi_filter      = 30,       # -> levels 20 / 80
    atr_period      = 1000,
    atr_mult_candle = 1.0,
    sl_atr_mult     = 2.0,
    trail_atr_mult  = 0.2,
    orderdist_mult  = 0.3,
    max_spread_pts  = 1000,     # points; XAUUSD median~517 p95~737 (EA default 10 = USDJPY)
    max_order_age   = 5,        # bars
    start_hour      = 0,
    end_hour        = 23,
    risk_pct        = 1.0,      # % of balance
    deposit         = 1000.0,
    commission_perlot_side = 0.0,
)

# per-instrument market spec
SPEC = dict(
    XAUUSD = dict(point=0.001, contract=100.0, min_lot=0.01, max_lot=100.0, lot_step=0.01),
    US500  = dict(point=0.1,   contract=1.0,   min_lot=0.01, max_lot=100.0, lot_step=0.01),
)

# -----------------------------------------------------------------------------
def load_ticks(symbol, files):
    frames = []
    for f in files:
        frames.append(pd.read_parquet(f, columns=['timestamp','bid_price','ask_price']))
    df = pd.concat(frames, ignore_index=True)
    df.sort_values('timestamp', inplace=True, kind='stable')
    df.reset_index(drop=True, inplace=True)
    ts  = df['timestamp'].values.astype('datetime64[ms]').astype(np.int64)  # ms
    bid = df['bid_price'].values.astype(np.float64)
    ask = df['ask_price'].values.astype(np.float64)
    return ts, bid, ask

def build_bars(ts, bid, tf_ms):
    bar_key = ts // tf_ms
    uniq, inv = np.unique(bar_key, return_inverse=True)  # inv = per-tick bar index
    nbars = len(uniq)
    # OHLC of bid per bar
    o = np.empty(nbars); h = np.full(nbars, -np.inf); l = np.full(nbars, np.inf); c = np.empty(nbars)
    # first / last via inv (ticks are time-sorted)
    o[inv[0]] = bid[0]
    first_seen = np.zeros(nbars, dtype=bool)
    # vectorised high/low
    np.maximum.at(h, inv, bid)
    np.minimum.at(l, inv, bid)
    # open = first tick's bid per bar, close = last tick's bid per bar
    # since sorted, find boundaries
    change = np.empty(len(inv), dtype=bool); change[0]=True; change[1:] = inv[1:]!=inv[:-1]
    starts = np.where(change)[0]
    o[inv[starts]] = bid[starts]
    ends = np.append(starts[1:]-1, len(inv)-1)
    c[inv[ends]] = bid[ends]
    # bar start time (ms) for hour-of-day
    bar_start_ms = uniq * tf_ms
    return inv.astype(np.int64), o, h, l, c, bar_start_ms

def bar_indicator_state(o,h,l,c, bb_p, rsi_p, atr_p, bb_dev):
    """Precompute completed-bar recursion state, aligned so index b = state ENTERING bar b."""
    n = len(c)
    # ---- BB rolling sum/sumsq of the (bb_p-1) completed closes preceding bar b ----
    k = bb_p - 1                      # 19 fixed completed closes; forming close added at tick time
    csum  = np.zeros(n); csumsq = np.zeros(n)
    cs = np.cumsum(c); cs2 = np.cumsum(c*c)
    for b in range(n):
        lo = b - k
        if lo < 0:
            csum[b] = np.nan; csumsq[b] = np.nan
        else:
            s  = cs[b-1]  - (cs[lo-1]  if lo-1>=0 else 0.0)
            s2 = cs2[b-1] - (cs2[lo-1] if lo-1>=0 else 0.0)
            csum[b] = s; csumsq[b] = s2
    prev_close = np.empty(n); prev_close[0]=np.nan; prev_close[1:] = c[:-1]

    # ---- RSI Wilder avg gain/loss at each completed bar ----
    change = np.empty(n); change[0]=0.0; change[1:] = c[1:]-c[:-1]
    gain = np.where(change>0, change, 0.0); loss = np.where(change<0, -change, 0.0)
    ag = np.full(n, np.nan); al = np.full(n, np.nan)
    if n > rsi_p:
        ag[rsi_p] = gain[1:rsi_p+1].mean(); al[rsi_p] = loss[1:rsi_p+1].mean()
        for b in range(rsi_p+1, n):
            ag[b] = (ag[b-1]*(rsi_p-1) + gain[b]) / rsi_p
            al[b] = (al[b-1]*(rsi_p-1) + loss[b]) / rsi_p
    # state entering bar b uses ag[b-1]
    rsi_ag_prev = np.full(n, np.nan); rsi_al_prev = np.full(n, np.nan)
    rsi_ag_prev[1:] = ag[:-1]; rsi_al_prev[1:] = al[:-1]

    # ---- ATR Wilder ----
    tr = np.empty(n); tr[0]=h[0]-l[0]
    pc = c[:-1]
    tr[1:] = np.maximum.reduce([h[1:]-l[1:], np.abs(h[1:]-pc), np.abs(l[1:]-pc)])
    atr = np.full(n, np.nan)
    if n > atr_p:
        atr[atr_p] = tr[1:atr_p+1].mean()
        for b in range(atr_p+1, n):
            atr[b] = (atr[b-1]*(atr_p-1) + tr[b]) / atr_p
    atr_prev = np.full(n, np.nan); atr_prev[1:] = atr[:-1]

    return csum, csumsq, prev_close, rsi_ag_prev, rsi_al_prev, atr_prev


@njit(cache=True)
def run(tick_bar, bid, ask, hour, ts,
        csum, csumsq, prev_close, rsi_ag_prev, rsi_al_prev, atr_prev,
        bb_p, bb_dev, rsi_p, rsi_lo, rsi_hi, atr_p,
        mult_candle, sl_mult, trail_mult, dist_mult,
        max_spread_pts, max_age_bars, start_hour, end_hour,
        point, contract, min_lot, max_lot, lot_step,
        risk_pct, deposit, commission, tf_ms, warmup_bar,
        tr_dir, tr_entry, tr_exit, tr_pnl, tr_bal, tr_ts_in, tr_ts_out, tr_reason):

    mode = 0              # 0 flat, 1 pending, 2 position
    p_type=0; p_price=0.0; p_sl=0.0; p_tp=0.0; p_setup=0; p_lots=0.0
    x_type=0; x_entry=0.0; x_sl=0.0; x_tp=0.0; x_lots=0.0; x_ts=0
    balance = deposit
    ntr = 0

    cur_bar = -1
    f_hi = 0.0; f_lo = 0.0    # forming bar running high/low (bid)

    n = len(bid)
    for i in range(n):
        b = tick_bar[i]
        bd = bid[i]; ak = ask[i]
        new_bar = (b != cur_bar)
        if new_bar:
            cur_bar = b
            f_hi = bd; f_lo = bd
        else:
            if bd > f_hi: f_hi = bd
            if bd < f_lo: f_lo = bd

        if b < warmup_bar:
            continue
        ap = atr_prev[b]
        if ap != ap:   # nan
            continue

        # ---------- forming-bar indicators (index 0) ----------
        c = bd                                   # forming close = bid
        mean = (csum[b] + c) / bb_p
        var  = (csumsq[b] + c*c) / bb_p - mean*mean
        if var < 0.0: var = 0.0
        sd = var ** 0.5
        bb_mid = mean
        bb_up  = mean + bb_dev * sd
        bb_lo  = mean - bb_dev * sd

        pc = prev_close[b]
        chg = c - pc
        g = chg if chg > 0.0 else 0.0
        ls = -chg if chg < 0.0 else 0.0
        ag = (rsi_ag_prev[b]*(rsi_p-1) + g) / rsi_p
        al = (rsi_al_prev[b]*(rsi_p-1) + ls) / rsi_p
        if al == 0.0:
            rsi = 100.0
        else:
            rsi = 100.0 - 100.0/(1.0 + ag/al)

        tr0 = f_hi - f_lo
        d1 = f_hi - pc;
        if d1 < 0: d1 = -d1
        d2 = f_lo - pc
        if d2 < 0: d2 = -d2
        if d1 > tr0: tr0 = d1
        if d2 > tr0: tr0 = d2
        atr = (ap*(atr_p-1) + tr0) / atr_p

        candle_size = f_hi - f_lo
        cand_thr = atr * mult_candle
        order_dist = atr * dist_mult
        sl_dist = atr * sl_mult
        trail_dist = atr * trail_mult

        # ================= manage OPEN POSITION (server-side exits + trailing) ==
        if mode == 2:
            closed = False
            if x_type > 0:   # BUY -> valued at bid
                if bd <= x_sl:
                    ex = bd if bd < x_sl else x_sl   # SL at market (worse)
                    pnl = (ex - x_entry)*contract*x_lots - commission*x_lots
                    balance += pnl; closed = True; reason = 0
                elif bd >= x_tp:
                    ex = x_tp
                    pnl = (ex - x_entry)*contract*x_lots - commission*x_lots
                    balance += pnl; closed = True; reason = 1
            else:            # SELL -> valued at ask
                if ak >= x_sl:
                    ex = ak if ak > x_sl else x_sl
                    pnl = (x_entry - ex)*contract*x_lots - commission*x_lots
                    balance += pnl; closed = True; reason = 0
                elif ak <= x_tp:
                    ex = x_tp
                    pnl = (x_entry - ex)*contract*x_lots - commission*x_lots
                    balance += pnl; closed = True; reason = 1
            if closed:
                tr_dir[ntr]=x_type; tr_entry[ntr]=x_entry; tr_exit[ntr]=ex
                tr_pnl[ntr]=pnl; tr_bal[ntr]=balance; tr_ts_in[ntr]=x_ts
                tr_ts_out[ntr]=ts[i]; tr_reason[ntr]=reason; ntr+=1
                mode = 0
            else:
                # trailing stop
                if x_type > 0:
                    if bd > x_entry:
                        nsl = bd - trail_dist
                        if nsl > x_entry and nsl > x_sl + point:
                            x_sl = nsl
                else:
                    if ak < x_entry:
                        nsl = ak + trail_dist
                        if nsl < x_entry and nsl < x_sl - point:
                            x_sl = nsl

        # ================= manage PENDING order =================================
        if mode == 1:
            filled = False
            if p_type > 0:   # BUY STOP: trigger when ask >= level
                if ak >= p_price:
                    x_type=1; x_entry=ak; x_sl=p_sl; x_tp=p_tp; x_lots=p_lots; x_ts=ts[i]
                    mode=2; filled=True
            else:            # SELL STOP: trigger when bid <= level
                if bd <= p_price:
                    x_type=-1; x_entry=bd; x_sl=p_sl; x_tp=p_tp; x_lots=p_lots; x_ts=ts[i]
                    mode=2; filled=True
            if not filled:
                # age expiry on new bar
                if new_bar and max_age_bars > 0:
                    age = ts[i] - p_setup
                    if age >= max_age_bars * tf_ms:
                        mode = 0
                if mode == 1:
                    # pending trailing to keep constant ATR gap toward price
                    if p_type > 0:
                        desired = ak + order_dist
                        if desired < p_price - point:
                            tp = bb_mid
                            if tp > desired:
                                p_price = desired; p_sl = desired - sl_dist; p_tp = tp
                    else:
                        desired = bd - order_dist
                        if desired > p_price + point:
                            tp = bb_mid
                            if tp < desired:
                                p_price = desired; p_sl = desired + sl_dist; p_tp = tp

        # ================= ENTRY (only when flat) ===============================
        if mode == 0:
            # session filter
            if start_hour <= end_hour:
                in_win = (hour[i] >= start_hour and hour[i] <= end_hour)
            else:
                in_win = (hour[i] >= start_hour or hour[i] <= end_hour)
            if in_win:
                spread_pts = (ak - bd) / point
                if spread_pts <= max_spread_pts:
                    big = candle_size > cand_thr
                    buy  = big and (bd < bb_lo) and (rsi < rsi_lo)
                    sell = big and (ak > bb_up) and (rsi > rsi_hi)
                    if buy or sell:
                        # lots
                        risk_money = balance * (risk_pct/100.0)
                        loss_per_lot = sl_dist * contract
                        lots = 0.0
                        if loss_per_lot > 0.0:
                            lots = risk_money / loss_per_lot
                            steps = np.floor(lots/lot_step)
                            lots = steps*lot_step
                            if lots < min_lot: lots = min_lot
                            if lots > max_lot: lots = max_lot
                        if lots > 0.0:
                            if buy:
                                price = ak + order_dist
                                tp = bb_mid
                                if tp > price:
                                    p_type=1; p_price=price; p_sl=price - sl_dist
                                    p_tp=tp; p_setup=ts[i]; p_lots=lots; mode=1
                            else:
                                price = bd - order_dist
                                tp = bb_mid
                                if tp < price:
                                    p_type=-1; p_price=price; p_sl=price + sl_dist
                                    p_tp=tp; p_setup=ts[i]; p_lots=lots; mode=1
    return ntr, balance


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='XAUUSD')
    ap.add_argument('--glob', default='XAUUSD/year=2025/month=0[1-6]/*.parquet')
    ap.add_argument('--out', default='equity.csv')
    ap.add_argument('--tf', type=int, default=P['tf_minutes'])
    args = ap.parse_args()
    P['tf_minutes'] = args.tf

    spec = SPEC[args.symbol]
    files = sorted(glob.glob(args.glob))
    if not files:
        print('No files match', args.glob); sys.exit(1)
    print(f'Loading {len(files)} files for {args.symbol} ...')
    t0=time.time()
    ts, bid, ask = load_ticks(args.symbol, files)
    print(f'  {len(ts):,} ticks  ({time.time()-t0:.1f}s)  '
          f'{np.datetime64(int(ts.min()),"ms")} -> {np.datetime64(int(ts.max()),"ms")}')

    tf_ms = P['tf_minutes']*60*1000
    tick_bar, o,h,l,c, bar_start_ms = build_bars(ts, bid, tf_ms)
    print(f'  {len(c):,} bars on M{P["tf_minutes"]}')

    csum,csumsq,prev_close,rag,ral,atr_prev = bar_indicator_state(
        o,h,l,c, P['bb_period'], P['rsi_period'], P['atr_period'], P['bb_dev'])

    hour = ((ts // 3600000) % 24).astype(np.int64)
    warmup_bar = P['atr_period'] + 2
    rsi_lo = 50.0 - P['rsi_filter']; rsi_hi = 50.0 + P['rsi_filter']

    N = len(bid)
    cap = 2_000_000
    tr_dir=np.zeros(cap,np.int64); tr_entry=np.zeros(cap); tr_exit=np.zeros(cap)
    tr_pnl=np.zeros(cap); tr_bal=np.zeros(cap); tr_ts_in=np.zeros(cap,np.int64)
    tr_ts_out=np.zeros(cap,np.int64); tr_reason=np.zeros(cap,np.int64)

    print('Running tick loop (JIT compiling first)...')
    t0=time.time()
    ntr, final_bal = run(
        tick_bar, bid, ask, hour, ts,
        csum,csumsq,prev_close,rag,ral,atr_prev,
        P['bb_period'], P['bb_dev'], P['rsi_period'], rsi_lo, rsi_hi, P['atr_period'],
        P['atr_mult_candle'], P['sl_atr_mult'], P['trail_atr_mult'], P['orderdist_mult'],
        float(P['max_spread_pts']), P['max_order_age'], P['start_hour'], P['end_hour'],
        spec['point'], spec['contract'], spec['min_lot'], spec['max_lot'], spec['lot_step'],
        P['risk_pct'], P['deposit'], P['commission_perlot_side'], tf_ms, warmup_bar,
        tr_dir,tr_entry,tr_exit,tr_pnl,tr_bal,tr_ts_in,tr_ts_out,tr_reason)
    print(f'  done: {ntr:,} trades  ({time.time()-t0:.1f}s)')

    # -------- metrics --------
    pnl = tr_pnl[:ntr]; bal = tr_bal[:ntr]; reason = tr_reason[:ntr]
    ts_out = tr_ts_out[:ntr]; direc = tr_dir[:ntr]
    if ntr==0:
        print('No trades.'); return
    eq = np.concatenate([[P['deposit']], bal])
    peak = np.maximum.accumulate(eq); dd = peak - eq
    dd_pct = dd/peak*100
    wins = pnl>0
    gross_p = pnl[pnl>0].sum(); gross_l = -pnl[pnl<0].sum()
    pf = gross_p/gross_l if gross_l>0 else float('inf')
    net = final_bal - P['deposit']

    print('\n================ BACKTEST SUMMARY ================')
    print(f'Symbol / TF        : {args.symbol}  M{P["tf_minutes"]}')
    print(f'Period             : {np.datetime64(int(ts.min()),"ms")}  ->  {np.datetime64(int(ts.max()),"ms")}')
    print(f'Deposit            : ${P["deposit"]:,.2f}')
    print(f'Final balance      : ${final_bal:,.2f}')
    print(f'Net profit         : ${net:,.2f}  ({net/P["deposit"]*100:.1f}%)')
    print(f'Total trades       : {ntr:,}')
    print(f'Win rate           : {wins.mean()*100:.1f}%   (wins {wins.sum():,} / losses {(~wins).sum():,})')
    print(f'  exits by TP      : {(reason==1).sum():,}')
    print(f'  exits by SL      : {(reason==0).sum():,}')
    print(f'Profit factor      : {pf:.2f}')
    print(f'Avg trade          : ${pnl.mean():.2f}   (win ${pnl[pnl>0].mean() if wins.any() else 0:.2f} / loss ${pnl[pnl<0].mean() if (~wins).any() else 0:.2f})')
    print(f'Largest win / loss : ${pnl.max():.2f} / ${pnl.min():.2f}')
    print(f'Max drawdown       : ${dd.max():.2f}  ({dd_pct.max():.1f}%)')
    print(f'Longs / Shorts     : {(direc>0).sum():,} / {(direc<0).sum():,}')
    print('==================================================')

    out = pd.DataFrame({
        'ts_out': pd.to_datetime(ts_out, unit='ms'),
        'dir': np.where(direc>0,'BUY','SELL'),
        'pnl': pnl, 'balance': bal,
        'exit': np.where(reason==1,'TP','SL'),
    })
    out.to_csv(args.out, index=False)
    print('Wrote', args.out)

if __name__ == '__main__':
    main()
