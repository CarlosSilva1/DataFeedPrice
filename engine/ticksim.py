"""Real-tick fills with latency: the "Every tick based on real ticks" pass.

For every order the bar engine would send, this finds the first real tick of
the next bar, adds the order latency (latency_ms +/- random jitter), and fills
at the first tick at or after that moment: ASK for buys, BID for sells, plus
slippage. Those fills replace the zero-latency ones in engine.backtest.run.

Used to re-check every combo that passes the rules before it reaches the
portfolio, so the final KPIs include latency.
"""
from __future__ import annotations

import glob
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from . import backtest

REPO = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=4)
def _ticks(sym: str, year: int, month: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    files = sorted(glob.glob(str(REPO / sym / f"year={year}" / f"month={month:02d}" / "*.parquet")))
    if not files:
        return np.array([], dtype="datetime64[ms]"), np.array([]), np.array([])
    t = pd.concat(pq.read_table(f, columns=["timestamp", "bid_price", "ask_price"]).to_pandas() for f in files)
    t = t[(t.bid_price > 0) & (t.ask_price >= t.bid_price)].sort_values("timestamp")
    return t.timestamp.to_numpy(), t.bid_price.to_numpy(), t.ask_price.to_numpy()


def tick_fills(df: pd.DataFrame, sig: pd.Series, sym: str, seed: int = 7) -> tuple[pd.Series, dict]:
    sp = backtest.spec(sym)
    rng = np.random.default_rng(seed)
    pos = sig.shift(1).fillna(0)
    delta = pos - pos.shift(1).fillna(0)
    adverse = (sp["slippage_points"] + sp["extra_spread_points"] / 2) * sp["point"]
    fills = backtest.bar_fills(df, delta, sp)  # fallback when no ticks are on disk
    lat_used = []
    for ts in df.index[delta.to_numpy() != 0]:
        times, bid, ask = _ticks(sym, ts.year, ts.month)
        if len(times) == 0:
            continue
        i0 = np.searchsorted(times, np.datetime64(ts, "ms"))            # first tick of the bar
        if i0 >= len(times):
            continue
        lat = max(0.0, sp["latency_ms"] + rng.uniform(-1, 1) * sp["latency_jitter_ms"])
        i = np.searchsorted(times, times[i0] + np.timedelta64(int(lat), "ms"))
        if i >= len(times):
            i = len(times) - 1
        d = delta.loc[ts]
        fills.loc[ts] = ask[i] + adverse if d > 0 else bid[i] - adverse
        lat_used.append(lat)
    return fills, {"orders": len(lat_used), "avg_latency_ms": float(np.mean(lat_used)) if lat_used else 0.0}


def run(df, sig, tf, sym) -> dict:
    fills, info = tick_fills(df, sig, sym)
    r = backtest.run(df, sig, tf, sym, fills=fills)
    r["execution"] = {"model": "real ticks + latency", **info}
    return r
