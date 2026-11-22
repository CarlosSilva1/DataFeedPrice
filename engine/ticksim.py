"""Real-tick fills with the live pipeline's delay: the "Every tick based on real ticks" pass.

For every order the bar engine would send, this takes the first real tick of the
new bar, adds the signal-to-order delay (signal_delay_minutes +/- jitter: the
time the scheduled task and the EA need after a bar closes) plus the network
latency (latency_ms +/- jitter), and fills at the first tick at or after that
moment: ASK for buys, BID for sells, plus slippage.

Every combo that passes the rules is re-run with these fills before it reaches
the portfolio, so the final KPIs include the real delay.
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


@lru_cache(maxsize=3)
def _ticks(sym: str, year: int, month: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    files = sorted(glob.glob(str(REPO / sym / f"year={year}" / f"month={month:02d}" / "*.parquet")))
    if not files:
        return np.array([], dtype="datetime64[ms]"), np.array([]), np.array([])
    t = pd.concat(pq.read_table(f, columns=["timestamp", "bid_price", "ask_price"]).to_pandas() for f in files)
    t = t[(t.bid_price > 0) & (t.ask_price >= t.bid_price)].sort_values("timestamp")
    return t.timestamp.to_numpy().astype("datetime64[ms]"), t.bid_price.to_numpy(), t.ask_price.to_numpy()


def first_tick(sym: str, t: np.datetime64):
    """(time, bid, ask) of the first tick at or after t, looking into the next month if needed."""
    ts = pd.Timestamp(t)
    for k in range(2):
        m = ts + pd.DateOffset(months=k)
        times, bid, ask = _ticks(sym, m.year, m.month)
        i = np.searchsorted(times, t)
        if i < len(times):
            return times[i], bid[i], ask[i]
    return None


def tick_fills(df: pd.DataFrame, sig: pd.Series, sym: str, seed: int = 7):
    sp = backtest.spec(sym)
    rng = np.random.default_rng(seed)
    fb, fs = backtest.bar_fills(df, sp)          # fallback where no ticks are on disk
    fb, fs = fb.copy(), fs.copy()
    adverse = (sp["slippage_points"] + sp["extra_spread_points"] / 2) * sp["point"]
    target = sig.shift(1).fillna(0)
    trade = (target != target.shift(1).fillna(0)).to_numpy()
    delays = []
    for ts, utc in zip(df.index[trade], df.utc[trade]):
        t0 = first_tick(sym, np.datetime64(utc, "ms"))
        if t0 is None:
            continue
        delay_ms = (max(0.0, sp["signal_delay_minutes"] + rng.uniform(-1, 1) * sp["signal_delay_jitter_minutes"]) * 60000
                    + max(0.0, sp["latency_ms"] + rng.uniform(-1, 1) * sp["latency_jitter_ms"]))
        hit = first_tick(sym, t0[0] + np.timedelta64(int(delay_ms), "ms"))
        if hit is None:
            continue
        fb.loc[ts], fs.loc[ts] = hit[2] + adverse, hit[1] - adverse
        delays.append((hit[0] - np.datetime64(utc, "ms")) / np.timedelta64(1, "m"))
    info = {"model": "real ticks + signal delay + latency", "orders": len(delays),
            "avg_minutes_after_bar_open": round(float(np.mean(delays)), 1) if delays else 0.0,
            "max_minutes_after_bar_open": round(float(np.max(delays)), 1) if delays else 0.0}
    return (fb, fs), info


def run(df, sig, tf, sym, exposure: float = 1.0) -> dict:
    fills, info = tick_fills(df, sig, sym)
    r = backtest.run(df, sig, tf, sym, exposure, fills=fills)
    r["execution"] = info
    r["_fills"] = fills
    return r
