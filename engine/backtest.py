"""MT5-style account simulator and KPIs.

Mirrors what the MT5 Strategy Tester does for an EA that acts on a new bar:
  - bars are BID bars on the broker server clock (see engine.bars),
  - the signal is decided on bar t's close; the order goes out when bar t+1 opens,
  - buys fill at the ASK, sells at the BID, plus slippage against you
    (plus extra_spread_points/2 if your broker is wider than the data feed),
  - a money account: deposit, real lots (volume_min / volume_step, rounded down),
    lot size fixed when the trade opens = exposure x equity / (price x contract),
  - commission per lot per side, swap charged at every server-midnight rollover
    the position is held through, tripled on the symbol's triple-swap weekday
    and not charged on weekend rollovers,
  - equity is marked at the bid.

`fills=(buy, sell)` lets engine.ticksim pass real-tick fills that include the
signal-to-order delay and latency; without it the bar's first tick is used.

Known simplifications (see engine/README.md): shorts are marked at bid instead
of ask (spread paid at exit instead of entry), no margin call / stop-out.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .bars import TF_DELTA

SPEC_PATH = Path(__file__).resolve().parent / "config" / "symbols.json"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_PRIVATE = ("returns", "equity", "bh_equity", "in_market", "trade_list", "_fills")


@lru_cache(None)
def _specs() -> dict:
    return json.loads(SPEC_PATH.read_text())


def spec(sym: str) -> dict:
    s = _specs()
    if sym not in s or sym in ("defaults", "account", "server_time", "_comment"):
        raise KeyError(f"No contract spec for {sym} in {SPEC_PATH}; add one before backtesting it.")
    return {**s["defaults"], **s[sym]}


def deposit() -> float:
    return float(_specs()["account"]["initial_deposit"])


def public(r: dict) -> dict:
    return {k: v for k, v in r.items() if k not in _PRIVATE}


def bar_fills(df: pd.DataFrame, sp: dict) -> tuple[pd.Series, pd.Series]:
    """Zero-delay fills on the bar's first tick: (buy at ask, sell at bid), with slippage."""
    adverse = (sp["slippage_points"] + sp["extra_spread_points"] / 2) * sp["point"]
    return df.open_ask + adverse, df.open_bid - adverse


def swap_weights(index: pd.DatetimeIndex, tf: str, triple_weekday: str) -> np.ndarray:
    """Per bar: number of swap charges for a position held from this bar's open to the
    next bar's open. One per server midnight crossed; 3 on the triple weekday's
    rollover; 0 for the Saturday and Sunday rollovers."""
    starts = index.normalize()
    ends = index[1:].append(pd.DatetimeIndex([index[-1] + TF_DELTA[tf]])).normalize()
    days = pd.date_range(starts[0] - pd.Timedelta("2D"), ends[-1] + pd.Timedelta("1D"))
    triple = WEEKDAYS.index(triple_weekday)
    w = np.where(days.dayofweek >= 5, 0, np.where(days.dayofweek == triple, 3, 1))
    c = pd.Series(np.cumsum(w), index=days)
    one = pd.Timedelta("1D")
    return (c.reindex(ends - one).to_numpy() - c.reindex(starts - one).to_numpy()).astype(float)


@dataclass
class Stream:
    """One asset+strategy on the simulation grid."""
    name: str
    sym: str
    open: np.ndarray       # bid at each grid step's open
    close: np.ndarray      # bid at each grid step's close
    target: np.ndarray     # signed exposure as a fraction of equity, held during the step
    trade: np.ndarray      # True where the target changes at this step's open
    fill_buy: np.ndarray
    fill_sell: np.ndarray
    swap_w: np.ndarray


def make_stream(name: str, df: pd.DataFrame, sig: pd.Series, tf: str, sym: str, exposure: float = 1.0,
                fills: tuple[pd.Series, pd.Series] | None = None, hold: bool = False) -> Stream:
    sp = spec(sym)
    if hold:
        target = np.full(len(df), exposure)
    else:
        target = (sig.shift(1).fillna(0) * exposure).to_numpy()
    trade = np.r_[target[0] != 0, target[1:] != target[:-1]]
    fb, fs = fills if fills is not None else bar_fills(df, sp)
    return Stream(name, sym, df.open.to_numpy(), df.close.to_numpy(), target, trade,
                  fb.to_numpy(), fs.to_numpy(), swap_weights(df.index, tf, sp["swap_triple_weekday"]))


def simulate(streams: list[Stream], n: int, dep: float | None = None) -> dict:
    """Run the money account over n grid steps. Returns equity per step and the trade list."""
    equity = dep if dep is not None else deposit()
    eq = np.empty(n)
    in_mkt = np.zeros(n, dtype=bool)
    S = []
    for s in streams:
        sp = spec(s.sym)
        S.append({"s": s, "lots": 0.0, "mark": 0.0, "pnl": 0.0, "entry_eq": 0.0, "entry_i": 0,
                  "cs": sp["contract_size"], "step": sp["volume_step"], "vmin": sp["volume_min"],
                  "comm": sp["commission_per_lot_per_side_usd"],
                  "swl": sp["swap_long_pct_per_year"] / 100 / 360, "sws": sp["swap_short_pct_per_year"] / 100 / 360,
                  "skipped": 0, "entries": 0})
    trades = []
    max_lev = 0.0
    for i in range(n):
        for st in S:                                   # mark open positions to the step's open
            if st["lots"]:
                d = st["lots"] * st["cs"] * (st["s"].open[i] - st["mark"])
                equity += d; st["pnl"] += d; st["mark"] = st["s"].open[i]
        for st in S:
            s = st["s"]
            if not s.trade[i]:
                continue
            if st["lots"]:                             # close (sell longs at bid, buy back shorts at ask)
                px = s.fill_sell[i] if st["lots"] > 0 else s.fill_buy[i]
                d = st["lots"] * st["cs"] * (px - st["mark"]) - abs(st["lots"]) * st["comm"]
                equity += d; st["pnl"] += d
                trades.append({"stream": s.name, "entry_i": st["entry_i"], "exit_i": i, "lots": st["lots"],
                               "pnl": st["pnl"], "pnl_pct": st["pnl"] / st["entry_eq"] * 100})
                st["lots"] = 0.0
            tgt = s.target[i]
            if tgt and equity > 0:                     # open with lots sized from current equity
                px = s.fill_buy[i] if tgt > 0 else s.fill_sell[i]
                lots = round(math.floor(abs(tgt) * equity / (px * st["cs"]) / st["step"] + 1e-9) * st["step"], 8)
                st["entries"] += 1
                if lots < st["vmin"] - 1e-12:
                    st["skipped"] += 1                 # deposit too small for the minimum lot
                else:
                    fee = lots * st["comm"]
                    st.update(lots=lots if tgt > 0 else -lots, mark=px, pnl=-fee, entry_eq=equity, entry_i=i)
                    equity -= fee
        notional = 0.0
        for st in S:                                   # mark to the step's close, then swap
            if st["lots"]:
                s = st["s"]
                d = st["lots"] * st["cs"] * (s.close[i] - st["mark"])
                st["mark"] = s.close[i]
                n_ = abs(st["lots"]) * st["cs"] * s.close[i]
                d += n_ * (st["swl"] if st["lots"] > 0 else st["sws"]) * s.swap_w[i]
                equity += d; st["pnl"] += d
                notional += n_
                in_mkt[i] = True
        eq[i] = equity
        if equity > 0:
            max_lev = max(max_lev, notional / equity)
        else:                                          # account blown
            eq[i:] = 0.0
            break
    for st in S:                                       # report still-open trades at the last mark
        if st["lots"]:
            trades.append({"stream": st["s"].name, "entry_i": st["entry_i"], "exit_i": n - 1, "lots": st["lots"],
                           "pnl": st["pnl"], "pnl_pct": st["pnl"] / st["entry_eq"] * 100, "open": True})
    return {"eq": eq, "in_market": in_mkt, "trades": trades, "max_leverage_used": max_lev,
            "skipped": {st["s"].name: (st["skipped"], st["entries"]) for st in S}}


def _mdd(eq: np.ndarray) -> float:
    peak = np.maximum.accumulate(eq)
    return float(((eq / peak) - 1).min() * -100)


def kpis(eq: np.ndarray, index: pd.DatetimeIndex, trades: list[dict], in_mkt: np.ndarray, start_equity: float) -> dict:
    """KPIs for an equity path that started at start_equity before index[0]."""
    ret = np.diff(np.r_[start_equity, eq]) / np.r_[start_equity, eq[:-1]]
    years = max((index[-1] - index[0]).days / 365.25, 1e-9)
    bpy = len(eq) / years                              # real bars per year, not an assumed constant
    sd = ret.std()
    neg = ret[ret < 0]
    pn = np.array([t["pnl"] for t in trades])
    gp, gl = pn[pn > 0].sum(), -pn[pn <= 0].sum()
    full = np.r_[start_equity, eq]
    mdd = _mdd(full)
    total = eq[-1] / start_equity
    cagr = (total ** (1 / years) - 1) * 100 if total > 0 else -100.0
    return {
        "net_return_pct": float((total - 1) * 100),
        "cagr_pct": float(cagr),
        "max_drawdown_pct": mdd,
        "sharpe": float(ret.mean() / sd * np.sqrt(bpy)) if sd > 0 else 0.0,
        "sortino": float(ret.mean() / neg.std() * np.sqrt(bpy)) if len(neg) > 1 and neg.std() > 0 else 0.0,
        "calmar": float(cagr / mdd) if mdd > 0 else 0.0,
        "ann_vol_pct": float(sd * np.sqrt(bpy) * 100),
        "trades": int(len(pn)),
        "win_rate_pct": float((pn > 0).mean() * 100) if len(pn) else 0.0,
        "profit_factor": float(gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0),
        "exposure_pct": float(in_mkt.mean() * 100),
        "bars": int(len(eq)),
        "bars_per_year": round(bpy, 1),
        "start": str(index[0]),
        "end": str(index[-1]),
    }


_BH_CACHE: dict = {}


def buy_hold(df: pd.DataFrame, tf: str, sym: str, dep: float | None = None) -> np.ndarray:
    """Buy & hold on the same CFD: bought on the first bar with the same fills, lots and swap."""
    key = (sym, tf, df.index[0], df.index[-1], len(df), dep)
    if key not in _BH_CACHE:
        s = make_stream("bh", df, None, tf, sym, 1.0, hold=True)
        _BH_CACHE[key] = simulate([s], len(df), dep)["eq"]
    return _BH_CACHE[key]


def run(df: pd.DataFrame, sig: pd.Series, tf: str, sym: str, exposure: float = 1.0,
        fills: tuple[pd.Series, pd.Series] | None = None, dep: float | None = None) -> dict:
    dep = dep if dep is not None else deposit()
    s = make_stream("s", df, sig, tf, sym, exposure, fills)
    r = simulate([s], len(df), dep)
    bh = buy_hold(df, tf, sym, dep)
    out = kpis(r["eq"], df.index, r["trades"], r["in_market"], dep)
    out.update({
        "bh_return_pct": float((bh[-1] / dep - 1) * 100),
        "bh_max_drawdown_pct": _mdd(np.r_[dep, bh]),
        "max_leverage_used": round(r["max_leverage_used"], 2),
        "skipped_entries": r["skipped"]["s"][0],
        "deposit": dep,
        "final_equity": float(r["eq"][-1]),
        "returns": pd.Series(np.diff(np.r_[dep, r["eq"]]) / np.r_[dep, r["eq"][:-1]], index=df.index),
        "equity": pd.Series(r["eq"], index=df.index),
        "bh_equity": pd.Series(bh, index=df.index),
        "in_market": r["in_market"],
        "trade_list": r["trades"],
    })
    return out


def window(r: dict, df: pd.DataFrame, tf: str, sym: str, i0: int, i1: int) -> dict:
    """KPIs of a full-run result restricted to bars [i0, i1): equity path re-based,
    trades by entry bar, buy & hold bought fresh at bar i0."""
    eq = r["equity"].to_numpy()
    start = eq[i0 - 1] if i0 > 0 else r["deposit"]
    tr = [t for t in r["trade_list"] if i0 <= t["entry_i"] < i1]
    out = kpis(eq[i0:i1], df.index[i0:i1], tr, r["in_market"][i0:i1], start)
    bh = buy_hold(df.iloc[i0:i1], tf, sym, r["deposit"])
    out["bh_return_pct"] = float((bh[-1] / r["deposit"] - 1) * 100)
    return out
