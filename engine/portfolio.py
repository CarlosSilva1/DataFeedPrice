"""Portfolio builder: the "Portfolio Prompt" as code.

1. Backtest every asset x strategy x timeframe x parameter set on the MT5-style
   account simulator (engine.backtest).
2. Per combo (asset + strategy + timeframe) choose parameters on the first 70%
   of the data (in-sample) and check them on the last 30% (out-of-sample).
3. Keep combos that, over the full period:
     - beat buy & hold on the same asset and timeframe,
     - have max drawdown < 50%,
     - are not "too good to be true" (see OUTLIER RULES).
4. Re-run every survivor on real ticks with the live execution delay; it must pass again.
5. Size each survivor by risk/reward (mean/variance, shrunk), with caps.
6. Simulate ONE account trading all combos with real lots (what the bot does);
   drop combos whose lot is below the broker minimum for the deposit, re-size.
7. Save the chosen combos to engine/hot_backtests/ and write a report.

Usage:
    python -m engine.portfolio                           # benchmark: absolute
    python -m engine.portfolio --benchmark risk_matched
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, bars, strategies, ticksim

REPO = Path(__file__).resolve().parent.parent
HOT_DIR = REPO / "engine" / "hot_backtests"

TIMEFRAMES = ["H4", "D1"]
IS_FRACTION = 0.7

# Selection rules
MAX_DD_PCT = 50.0
# OUTLIER RULES ("too good to be true")
MIN_TRADES = 20            # fewer trades = result is mostly luck
MAX_SHARPE = 3.0           # sustained Sharpe > 3 on bars is almost always a bug or curve fit
MAX_PROFIT_FACTOR = 5.0
MAX_WIN_RATE = 85.0
MIN_OOS_SHARPE_RATIO = 0.3  # out-of-sample Sharpe must keep >= 30% of in-sample Sharpe
MIN_PARAM_ROBUSTNESS = 0.5  # >= 50% of the strategy's parameter sets must be profitable in-sample
ROBUST_Z_MAX = 3.5          # net return more than 3.5 MADs above the median of all tested combos

# Allocation
MAX_PER_COMBO = 0.30
MAX_PER_ASSET = 0.60
SHRINK = 0.5               # blend of risk/reward weights with equal risk weights
MAX_SKIPPED_ENTRIES = 0.2  # combo is untradable if > 20% of its entries fall below the minimum lot

# Benchmark mode
#   absolute     : strategy at 1x must beat buy & hold's return (the rule as written)
#   risk_matched : strategy is levered/delevered to buy & hold's volatility
#                  (max MAX_LEVERAGE) and must then beat buy & hold's return
BENCHMARK = "absolute"
MAX_LEVERAGE = 3.0


def _daily(r: dict) -> pd.Series:
    return (1 + r["returns"]).resample("1D").prod().sub(1)


def _set_result(c: dict, full: dict) -> None:
    df, tf, sym = c["_df"], c["timeframe"], c["asset"]
    k = int(len(df) * IS_FRACTION)
    c["_res"] = full
    c["full"] = backtest.public(full)
    c["in_sample"] = backtest.window(full, df, tf, sym, 0, k)
    c["out_of_sample"] = backtest.window(full, df, tf, sym, k, len(df))
    c["_daily"] = _daily(full)


def research(symbols: list[str]) -> list[dict]:
    combos = []
    for sym in symbols:
        for tf in TIMEFRAMES:
            df = bars.load_bars(sym, tf)
            k = int(len(df) * IS_FRACTION)
            for name, grid in strategies.GRID.items():
                tried = []
                for p in grid:
                    sig = strategies.signal(name, df, p)
                    full = backtest.run(df, sig, tf, sym)
                    tried.append((p, backtest.window(full, df, tf, sym, 0, k), sig, full))
                eligible = [t for t in tried if t[1]["trades"] >= MIN_TRADES * IS_FRACTION] or tried
                p, r_is, sig, full = max(eligible, key=lambda t: t[1]["sharpe"])
                c = {"id": f"{sym}|{name}|{tf}", "asset": sym, "strategy": name, "timeframe": tf, "params": p,
                     "leverage": 1.0, "engine": "bar open (first tick)",
                     "param_robustness": float(np.mean([t[1]["net_return_pct"] > 0 for t in tried])),
                     "_df": df, "_sig": sig, "_fills": None}
                _set_result(c, full)
                combos.append(c)
                f, o = c["full"], c["out_of_sample"]
                print(f"  {sym:7s} {tf} {name:20s} net {f['net_return_pct']:8.1f}%  B&H {f['bh_return_pct']:7.1f}%  "
                      f"DD {f['max_drawdown_pct']:5.1f}%  Sh {f['sharpe']:5.2f}  OOS Sh {o['sharpe']:5.2f}")
    return combos


def risk_match(c: dict) -> None:
    """Scale the combo to buy & hold's volatility, then re-run it."""
    r = c["_res"]
    bh_vol = r["bh_equity"].pct_change().std()
    vol = r["returns"].std()
    k = float(np.clip(bh_vol / vol, 0.25, MAX_LEVERAGE)) if vol > 0 else 1.0
    c["leverage"] = round(k, 2)
    c["full_1x"] = c["full"]
    _set_result(c, backtest.run(c["_df"], c["_sig"], c["timeframe"], c["asset"], c["leverage"]))


def tick_verify(c: dict) -> None:
    """Re-run a combo on real ticks with the live delay and replace its KPIs."""
    c["bar_engine_full"] = c["full"]
    full = ticksim.run(c["_df"], c["_sig"], c["timeframe"], c["asset"], c["leverage"])
    c["_fills"] = full["_fills"]
    _set_result(c, full)
    c["engine"] = full["execution"]["model"]


def apply_rules(combos: list[dict]) -> None:
    nets = np.array([c["full"]["net_return_pct"] / max(c["leverage"], 1e-9) for c in combos])
    med = np.median(nets)
    mad = np.median(np.abs(nets - med)) or 1.0
    for c in combos:
        f, i, o = c["full"], c["in_sample"], c["out_of_sample"]
        why = []
        if f["net_return_pct"] <= f["bh_return_pct"]:
            why.append(f"does not beat buy & hold ({f['net_return_pct']:.1f}% vs {f['bh_return_pct']:.1f}%)")
        if f["max_drawdown_pct"] >= MAX_DD_PCT:
            why.append(f"max drawdown {f['max_drawdown_pct']:.1f}% >= {MAX_DD_PCT}%")
        if c.get("lot_too_small"):
            why.append(c["lot_too_small"])
        out = []
        if f["trades"] < MIN_TRADES:
            out.append(f"only {f['trades']} trades")
        if f["sharpe"] > MAX_SHARPE:
            out.append(f"Sharpe {f['sharpe']:.2f} > {MAX_SHARPE}")
        if f["profit_factor"] > MAX_PROFIT_FACTOR:
            out.append(f"profit factor {f['profit_factor']:.2f} > {MAX_PROFIT_FACTOR}")
        if f["win_rate_pct"] > MAX_WIN_RATE:
            out.append(f"win rate {f['win_rate_pct']:.0f}% > {MAX_WIN_RATE}%")
        if (f["net_return_pct"] / c["leverage"] - med) / (1.4826 * mad) > ROBUST_Z_MAX:
            out.append("return is a statistical outlier vs all tested combos")
        if o["sharpe"] <= 0 or (i["sharpe"] > 0 and o["sharpe"] < MIN_OOS_SHARPE_RATIO * i["sharpe"]):
            out.append(f"falls apart out-of-sample (Sharpe {i['sharpe']:.2f} -> {o['sharpe']:.2f})")
        if c["param_robustness"] < MIN_PARAM_ROBUSTNESS:
            out.append(f"only {c['param_robustness']:.0%} of parameter sets profitable (curve fit)")
        c["rejected_rules"] = why
        c["outlier_flags"] = out
        c["selected"] = not why and not out


def allocate(sel: list[dict]) -> None:
    """w ~ mean/variance of daily returns (Kelly direction), shrunk toward equal
    risk, then capped per combo and per asset. Uncapped remainder stays cash."""
    if not sel:
        return
    mu = np.array([c["_daily"].mean() for c in sel])
    var = np.array([c["_daily"].var() for c in sel])
    vol = np.sqrt(var)
    kelly = np.clip(mu / var, 0, None)
    kelly = kelly / kelly.sum() if kelly.sum() > 0 else np.ones(len(sel)) / len(sel)
    eqrisk = (1 / vol) / (1 / vol).sum()
    w = SHRINK * kelly + (1 - SHRINK) * eqrisk
    assets = np.array([c["asset"] for c in sel])
    for _ in range(50):  # iterative capping with redistribution
        w = np.minimum(w, MAX_PER_COMBO)
        for a in set(assets):
            m = assets == a
            if w[m].sum() > MAX_PER_ASSET:
                w[m] *= MAX_PER_ASSET / w[m].sum()
        free = 1 - w.sum()
        room = np.array([
            min(MAX_PER_COMBO - w[k], MAX_PER_ASSET - w[assets == assets[k]].sum()) for k in range(len(w))
        ]).clip(0)
        if free < 1e-6 or room.sum() < 1e-6:
            break
        w += free * room / room.sum() * (room > 0)
    for c, x in zip(sel, w):
        c["nav_pct"] = round(float(x) * 100, 2)


def simulate_account(sel: list[dict]) -> tuple[dict, pd.Series, pd.Series]:
    """One money account trading every combo with real lots on an hourly grid:
    each combo opens lots = %NAV x leverage x account equity / (price x contract)."""
    h1 = {a: bars.load_bars(a, "H1").set_index("utc") for a in sorted({c["asset"] for c in sel})}
    grid = sorted(set().union(*[set(h.index) for h in h1.values()]))
    grid = pd.DatetimeIndex(grid)
    n = len(grid)

    def marks(sym):
        h = h1[sym].reindex(grid)
        close = h.close.ffill().bfill()
        opn = h.open.fillna(close.shift(1)).bfill()
        sw = pd.Series(backtest.swap_weights(bars.to_server(h1[sym].index), "H1",
                                             backtest.spec(sym)["swap_triple_weekday"]), index=h1[sym].index)
        return opn.to_numpy(), close.to_numpy(), sw.reindex(grid).fillna(0).to_numpy(), h

    def on_grid(series_by_utc, fill=None):
        return series_by_utc.reindex(grid)

    cache = {a: marks(a) for a in h1}
    streams = []
    for c in sel:
        df, sym = c["_df"], c["asset"]
        opn, close, sw, _ = cache[sym]
        expo = c["nav_pct"] / 100 * c["leverage"]
        tgt = pd.Series((c["_sig"].shift(1).fillna(0) * expo).to_numpy(), index=df.utc.to_numpy())
        tgt_g = tgt.reindex(grid).ffill().fillna(0).to_numpy()
        changed = pd.Series(np.r_[tgt.iloc[0] != 0, tgt.to_numpy()[1:] != tgt.to_numpy()[:-1]], index=tgt.index)
        trade = changed.reindex(grid).fillna(False).to_numpy(dtype=bool)
        fb, fs = c["_fills"] if c["_fills"] is not None else backtest.bar_fills(df, backtest.spec(sym))
        fbg = pd.Series(fb.to_numpy(), index=tgt.index).reindex(grid).to_numpy()
        fsg = pd.Series(fs.to_numpy(), index=tgt.index).reindex(grid).to_numpy()
        streams.append(backtest.Stream(c["id"], sym, opn, close, tgt_g, trade, fbg, fsg, sw))
    acct = backtest.simulate(streams, n)

    bh_streams = []
    for a in h1:
        opn, close, sw, h = cache[a]
        w = sum(c["nav_pct"] for c in sel if c["asset"] == a) / 100
        sp = backtest.spec(a)
        adverse = (sp["slippage_points"] + sp["extra_spread_points"] / 2) * sp["point"]
        ask0 = h.open_ask.bfill().to_numpy() + adverse
        trade = np.zeros(n, dtype=bool); trade[0] = True
        bh_streams.append(backtest.Stream(f"bh {a}", a, opn, close, np.full(n, w), trade, ask0, opn, sw))
    bh = backtest.simulate(bh_streams, n)

    dep = backtest.deposit()
    idx = bars.to_server(grid)
    k = backtest.kpis(acct["eq"], idx, acct["trades"], acct["in_market"], dep)
    k.update({
        "bh_return_pct": float((bh["eq"][-1] / dep - 1) * 100),
        "bh_max_drawdown_pct": backtest._mdd(np.r_[dep, bh["eq"]]),
        "deposit": dep, "final_equity": float(acct["eq"][-1]),
        "max_leverage_used": round(acct["max_leverage_used"], 2),
        "cash_pct": round(100 - sum(c["nav_pct"] for c in sel), 2),
        "skipped_entries": {name: f"{s}/{e}" for name, (s, e) in acct["skipped"].items()},
    })
    for c in sel:
        s, e = acct["skipped"][c["id"]]
        c["_skipped_ratio"] = s / e if e else 0.0
    return k, pd.Series(acct["eq"], index=idx), pd.Series(bh["eq"], index=idx)


def save(combos, sel, pk, eq, bh_eq) -> Path:
    HOT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    clean = lambda c: {k: v for k, v in c.items() if not k.startswith("_")}
    portfolio = {"generated_at": now, "benchmark": BENCHMARK, "portfolio_kpis": pk, "combos": [clean(c) for c in sel]}
    (HOT_DIR / f"portfolio_{BENCHMARK}.json").write_text(json.dumps(portfolio, indent=2))
    (HOT_DIR / f"all_combos_{BENCHMARK}.json").write_text(json.dumps([clean(c) for c in combos], indent=2))

    # Hot Backtests: a running list per benchmark; a combo stays in it with its latest result.
    hot_path = HOT_DIR / "hot_backtests.json"
    allhot = json.loads(hot_path.read_text()) if hot_path.exists() else {}
    hot = allhot.setdefault(BENCHMARK, {})
    for c in sel:
        hot[c["id"]] = {**clean(c), "saved_at": now, "in_current_portfolio": True}
    for k in hot:
        if k not in {c["id"] for c in sel}:
            hot[k]["in_current_portfolio"] = False
    hot_path.write_text(json.dumps(allhot, indent=2))

    if len(eq):
        daily = pd.DataFrame({"portfolio_equity": eq, "buy_hold_same_weights": bh_eq}).resample("1D").last().dropna()
        daily.to_csv(HOT_DIR / f"portfolio_equity_{BENCHMARK}.csv", float_format="%.2f")
    report = HOT_DIR / f"PORTFOLIO_REPORT_{BENCHMARK}.md"
    report.write_text(_report(now, combos, sel, pk))
    return report


def _report(now, combos, sel, pk) -> str:
    L = [f"# Portfolio report ({now})", "",
         "Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.",
         f"Benchmark mode: **{BENCHMARK}**. MT5-style simulation: bid bars on the server clock, money account with "
         "real lots, ask/bid fills with slippage, commission, swap with triple day; portfolio combos re-verified on "
         "real ticks with the live signal delay.", "",
         "## Portfolio", "",
         "| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(sel, key=lambda c: -c["nav_pct"]):
        f = c["full"]
        L.append(f"| {c['id']} | `{json.dumps(c['params'])}` | **{c['nav_pct']}** | {c['leverage']}x | {f['net_return_pct']:.1f} | "
                 f"{f['bh_return_pct']:.1f} | {f['max_drawdown_pct']:.1f} | {f['sharpe']:.2f} | "
                 f"{c['out_of_sample']['sharpe']:.2f} | {f['trades']} | {f['win_rate_pct']:.0f} | {f['profit_factor']:.2f} |")
    L += ["", "Per-combo numbers are the combo alone on the full deposit at its leverage."]
    if pk:
        L += ["", "## One account trading all combos (what the bot does)", "",
              f"- Deposit {pk['deposit']:,.0f} -> final equity {pk['final_equity']:,.0f} "
              f"(net {pk['net_return_pct']:.1f}%, CAGR {pk['cagr_pct']:.1f}%)",
              f"- Max drawdown {pk['max_drawdown_pct']:.1f}%, Sharpe {pk['sharpe']:.2f}, profit factor "
              f"{pk['profit_factor']:.2f}, {pk['trades']} trades, win rate {pk['win_rate_pct']:.0f}%",
              f"- Max leverage used {pk['max_leverage_used']}x, cash {pk['cash_pct']}%",
              f"- Buy & hold of the same assets at the same weights: {pk['bh_return_pct']:.1f}%, max DD {pk['bh_max_drawdown_pct']:.1f}%",
              f"- Entries skipped because the lot was below the broker minimum: {pk['skipped_entries']}",
              f"- Period {pk['start'][:10]} -> {pk['end'][:10]} (server time)"]
    L += ["", "## Rejected combos", "", "| Combo | Net % | B&H % | Max DD % | Why |", "|---|---|---|---|---|"]
    for c in combos:
        if not c["selected"]:
            f = c["full"]
            L.append(f"| {c['id']} | {f['net_return_pct']:.1f} | {f['bh_return_pct']:.1f} | {f['max_drawdown_pct']:.1f} | "
                     f"{'; '.join(c['rejected_rules'] + ['outlier: ' + x for x in c['outlier_flags']])} |")
    L += ["", "Past results do not predict future returns. Not investment advice."]
    return "\n".join(L) + "\n"


def main(symbols=None, benchmark=None):
    global BENCHMARK
    BENCHMARK = benchmark or BENCHMARK
    symbols = symbols or bars.available_symbols()
    print(f"Researching {symbols} on {TIMEFRAMES} (benchmark: {BENCHMARK}, deposit {backtest.deposit():,.0f})")
    combos = research(symbols)
    if BENCHMARK == "risk_matched":
        for c in combos:
            risk_match(c)
    apply_rules(combos)
    # Final gate: every survivor is re-run on real ticks with the live delay and must pass again.
    survivors = [c for c in combos if c["selected"]]
    if survivors:
        print(f"Tick-verifying {len(survivors)} survivors (real ticks + signal delay)...")
        for c in survivors:
            tick_verify(c)
        apply_rules(combos)
    pk, eq, bh_eq = {}, pd.Series(dtype=float), pd.Series(dtype=float)
    while True:  # size, simulate the shared account, drop combos the deposit cannot trade, repeat
        sel = [c for c in combos if c["selected"]]
        if not sel:
            pk, eq, bh_eq = {}, pd.Series(dtype=float), pd.Series(dtype=float)
            break
        allocate(sel)
        pk, eq, bh_eq = simulate_account(sel)
        small = [c for c in sel if c["_skipped_ratio"] > MAX_SKIPPED_ENTRIES]
        if not small:
            break
        for c in small:
            c["lot_too_small"] = (f"lot below broker minimum at {c['nav_pct']}% NAV x {c['leverage']}x "
                                  f"of a {backtest.deposit():,.0f} deposit")
            print(f"  dropping {c['id']}: {c['lot_too_small']}")
        apply_rules(combos)
    report = save(combos, sel, pk, eq, bh_eq)
    print(f"\n{len(sel)} of {len(combos)} combos selected. Report: {report.relative_to(REPO)}")
    for c in sorted(sel, key=lambda c: -c["nav_pct"]):
        print(f"  {c['nav_pct']:6.2f}%  x{c['leverage']}  {c['id']}  {c['params']}")
    if pk:
        print(f"Account: net {pk['net_return_pct']:.1f}%  DD {pk['max_drawdown_pct']:.1f}%  Sharpe {pk['sharpe']:.2f}  "
              f"vs B&H {pk['bh_return_pct']:.1f}% (DD {pk['bh_max_drawdown_pct']:.1f}%)")
    return sel


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--benchmark", choices=["absolute", "risk_matched"])
    a = ap.parse_args()
    main(a.symbols, a.benchmark)
