"""Bar backtester with an MT5-style execution model, plus KPIs.

How a trade is filled (same as an MT5 EA that acts on a new bar):
  - the signal is decided on bar t's close,
  - the order is sent on the first tick of bar t+1,
  - buys fill at the ASK and sells at the BID of that tick, plus slippage
    (and plus extra_spread_points/2 if your broker is wider than the data feed),
  - commission is charged per lot per side,
  - swap is charged on every rollover the position is held through
    (calendar-day counting = MT5's triple-Wednesday weekly total).
Positions are marked to mid between trades.

`run(..., fills=...)` lets engine.ticksim pass real tick fills that include
latency; without it, the first tick of the bar (zero latency) is used.

Sizing: position 1.0 = notional equal to current equity (1x), compounded.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

BARS_PER_YEAR = {"H1": 252 * 23, "H4": 252 * 6, "D1": 252}
SPEC_PATH = Path(__file__).resolve().parent / "config" / "symbols.json"
TF_DELTA = {"H1": pd.Timedelta("1h"), "H4": pd.Timedelta("4h"), "D1": pd.Timedelta("1D")}


@lru_cache(None)
def _specs() -> dict:
    return json.loads(SPEC_PATH.read_text())


def spec(sym: str) -> dict:
    s = _specs()
    if sym not in s:
        raise KeyError(f"No contract spec for {sym} in {SPEC_PATH}; add one before backtesting it.")
    return {**s["defaults"], **s[sym]}


def bar_fills(df: pd.DataFrame, delta: pd.Series, sp: dict) -> pd.Series:
    """Zero-latency fill on the bar's first tick: ask for buys, bid for sells."""
    adverse = (sp["slippage_points"] + sp["extra_spread_points"] / 2) * sp["point"]
    return pd.Series(np.where(delta > 0, df.open_ask + adverse, df.open_bid - adverse), index=df.index)


def _rollovers(idx: pd.DatetimeIndex, tf: str, hour: int) -> np.ndarray:
    """Number of rollovers (hour:00 UTC) inside each bar."""
    starts = idx.to_series()
    ends = starts.shift(-1).fillna(starts.iloc[-1] + TF_DELTA[tf])
    k = lambda t: ((t - pd.Timedelta(hours=hour)).dt.floor("1D"))
    return ((k(ends - pd.Timedelta("1ms")) - k(starts)).dt.days).clip(lower=0).to_numpy()


def run(df: pd.DataFrame, sig: pd.Series, tf: str, sym: str, fills: pd.Series | None = None) -> dict:
    sp = spec(sym)
    mid_open = (df.open_bid + df.open_ask) / 2
    close = df.close
    prev_close = close.shift(1).fillna(mid_open)
    pos = sig.shift(1).fillna(0)                       # held during bar t, traded at bar t open
    prev = pos.shift(1).fillna(0)
    delta = pos - prev
    if fills is None:
        fills = bar_fills(df, delta, sp)
    fills = fills.where(delta != 0, mid_open)
    pnl = prev * (mid_open - prev_close) + pos * (close - mid_open) - delta * (fills - mid_open)
    commission = delta.abs() * sp["commission_per_lot_per_side_usd"] / sp["contract_size"]
    ret = (pnl - commission) / prev_close
    rolls = _rollovers(df.index, tf, sp["rollover_utc_hour"])
    swap_rate = np.where(pos > 0, sp["swap_long_pct_per_year"], sp["swap_short_pct_per_year"]) / 100 / 360
    ret = ret + pos.abs() * swap_rate * rolls
    eq = (1 + ret).cumprod()

    # Buy & hold on the same CFD: same fills, same swap.
    bh_eq = (1 + run_bh(df, tf, sym)).cumprod()
    out = {"returns": ret, "equity": eq, "bh_equity": bh_eq, "position": pos}
    out.update(kpis(ret, eq, bh_eq, pos, tf))
    out["costs_pct_of_start"] = {
        "spread_slippage": float((delta * (fills - mid_open) / prev_close).sum() * 100),
        "commission": float((commission / prev_close).sum() * 100),
        "swap": float(-(pos.abs() * swap_rate * rolls).sum() * 100),
    }
    return out


def run_bh(df, tf, sym) -> pd.Series:
    sp = spec(sym)
    mid_open = (df.open_bid + df.open_ask) / 2
    close = df.close
    prev_close = close.shift(1).fillna(mid_open)
    pos = pd.Series(1.0, index=df.index)
    prev = pos.shift(1).fillna(0)
    delta = pos - prev
    fills = bar_fills(df, delta, sp).where(delta != 0, mid_open)
    pnl = prev * (mid_open - prev_close) + pos * (close - mid_open) - delta * (fills - mid_open)
    ret = (pnl - delta.abs() * sp["commission_per_lot_per_side_usd"] / sp["contract_size"]) / prev_close
    rolls = _rollovers(df.index, tf, sp["rollover_utc_hour"])
    return ret + sp["swap_long_pct_per_year"] / 100 / 360 * rolls


def _mdd(eq: pd.Series) -> float:
    return float((eq / eq.cummax() - 1).min() * -100)


def _trades(ret: pd.Series, pos: pd.Series) -> np.ndarray:
    """Compounded return of each trade (a run of constant non-zero position)."""
    seg = (pos != pos.shift()).cumsum()
    mask = pos != 0
    if not mask.any():
        return np.array([])
    return ((1 + ret[mask]).groupby(seg[mask]).prod() - 1).to_numpy()


def kpis(ret, eq, bh, pos, tf) -> dict:
    years = max((ret.index[-1] - ret.index[0]).days / 365.25, 1e-9)
    bpy = BARS_PER_YEAR[tf]
    sd = ret.std()
    dn = ret[ret < 0].std()
    tr = _trades(ret, pos)
    wins, losses = tr[tr > 0], tr[tr <= 0]
    mdd = _mdd(eq)
    cagr = (eq.iloc[-1] ** (1 / years) - 1) * 100 if eq.iloc[-1] > 0 else -100.0
    return {
        "net_return_pct": float((eq.iloc[-1] - 1) * 100),
        "cagr_pct": float(cagr),
        "max_drawdown_pct": mdd,
        "sharpe": float(ret.mean() / sd * np.sqrt(bpy)) if sd > 0 else 0.0,
        "sortino": float(ret.mean() / dn * np.sqrt(bpy)) if dn and dn > 0 else 0.0,
        "calmar": float(cagr / mdd) if mdd > 0 else 0.0,
        "ann_vol_pct": float(sd * np.sqrt(bpy) * 100),
        "trades": int(len(tr)),
        "win_rate_pct": float(len(wins) / len(tr) * 100) if len(tr) else 0.0,
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else (99.0 if len(wins) else 0.0),
        "exposure_pct": float((pos != 0).mean() * 100),
        "bh_return_pct": float((bh.iloc[-1] - 1) * 100),
        "bh_max_drawdown_pct": _mdd(bh),
        "bars": len(ret),
        "start": str(ret.index[0]),
        "end": str(ret.index[-1]),
    }
