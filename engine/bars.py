"""Build OHLC bars from the repo's tick parquet files.

Ticks (bid/ask) -> H1 mid-price bars with the average spread per bar.
H4 and D1 are resampled from H1 on load, so only H1 is cached on disk.

Usage:
    python -m engine.bars                 # build every instrument found in the repo
    python -m engine.bars --symbols US500
"""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parent.parent
BARS_DIR = REPO / "engine" / "data" / "bars"

TF_RULES = {"H1": "1h", "H4": "4h", "D1": "1D"}


def tick_symbols() -> list[str]:
    """Instrument folders in the repo root that hold tick parquet files."""
    out = []
    for d in sorted(REPO.iterdir()):
        if d.is_dir() and glob.glob(str(d / "year=*" / "month=*" / "*.parquet")):
            out.append(d.name)
    return out


def _file_to_h1(path: str) -> pd.DataFrame:
    t = pq.read_table(path, columns=["timestamp", "bid_price", "ask_price"]).to_pandas()
    t = t[(t.bid_price > 0) & (t.ask_price >= t.bid_price)]
    t["mid"] = (t.bid_price + t.ask_price) / 2
    t["spread"] = t.ask_price - t.bid_price
    g = t.set_index("timestamp").resample("1h")
    bars = g["mid"].ohlc()
    bars["spread"] = g["spread"].mean()
    bars["open_bid"] = g["bid_price"].first()   # first real tick of the bar:
    bars["open_ask"] = g["ask_price"].first()   # where an MT5 "new bar" EA gets filled
    bars["ticks"] = g["mid"].count()
    return bars[bars.ticks > 0]


def build_symbol(sym: str) -> Path:
    files = sorted(glob.glob(str(REPO / sym / "year=*" / "month=*" / "*.parquet")))
    parts = []
    for i, f in enumerate(files, 1):
        parts.append(_file_to_h1(f))
        if i % 20 == 0:
            print(f"  {sym}: {i}/{len(files)} files")
    h1 = pd.concat(parts)
    # A month can be split over several part files: merge overlapping hours.
    h1 = h1.groupby(level=0).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "mean",
         "open_bid": "first", "open_ask": "first", "ticks": "sum"}
    ).sort_index()
    BARS_DIR.mkdir(parents=True, exist_ok=True)
    out = BARS_DIR / f"{sym}_H1.csv.gz"
    h1.to_csv(out, float_format="%.5f")
    print(f"{sym}: {len(h1)} H1 bars {h1.index[0]} -> {h1.index[-1]} -> {out.relative_to(REPO)}")
    return out


def load_bars(sym: str, tf: str = "H1") -> pd.DataFrame:
    h1 = pd.read_csv(BARS_DIR / f"{sym}_H1.csv.gz", index_col=0, parse_dates=True)
    live = BARS_DIR / f"{sym}_H1_live.csv.gz"  # appended by engine.livefeed
    if live.exists():
        lv = pd.read_csv(live, index_col=0, parse_dates=True)
        h1 = pd.concat([h1, lv[lv.index > h1.index[-1]]])
    if tf == "H1":
        return h1
    r = h1.resample(TF_RULES[tf])
    out = pd.DataFrame(
        {"open": r.open.first(), "high": r.high.max(), "low": r.low.min(), "close": r.close.last(),
         "spread": r.spread.mean(), "open_bid": r.open_bid.first(), "open_ask": r.open_ask.first(),
         "ticks": r.ticks.sum()}
    )
    return out.dropna(subset=["close"])


def available_symbols() -> list[str]:
    return sorted(p.name.replace("_H1.csv.gz", "") for p in BARS_DIR.glob("*_H1.csv.gz"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    a = ap.parse_args()
    for s in a.symbols or tick_symbols():
        build_symbol(s)
