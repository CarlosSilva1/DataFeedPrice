"""Build MT5-style OHLC bars from the repo's tick parquet files.

Like MT5 charts, bars are built from BID prices and D1/H4 bars are cut on the
broker SERVER clock (engine/config/symbols.json > server_time; default New York
close = 00:00), so there are 5 daily bars per week and no Sunday stub bar.

On disk only H1 bars are cached, indexed in UTC. `load_bars` returns bars
indexed in server time with a `utc` column (UTC start of the bar).

Usage:
    python -m engine.bars                 # build every instrument found in the repo
    python -m engine.bars --symbols US500
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parent.parent
BARS_DIR = REPO / "engine" / "data" / "bars"
SPEC_PATH = REPO / "engine" / "config" / "symbols.json"

TF_RULES = {"H1": "1h", "H4": "4h", "D1": "1D"}
TF_DELTA = {"H1": pd.Timedelta("1h"), "H4": pd.Timedelta("4h"), "D1": pd.Timedelta("1D")}
AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "mean",
       "open_bid": "first", "open_ask": "first", "ticks": "sum"}


def tick_symbols() -> list[str]:
    """Instrument folders in the repo root that hold tick parquet files."""
    out = []
    for d in sorted(REPO.iterdir()):
        if d.is_dir() and glob.glob(str(d / "year=*" / "month=*" / "*.parquet")):
            out.append(d.name)
    return out


def ticks_to_h1(t: pd.DataFrame) -> pd.DataFrame:
    """Ticks (timestamp, bid_price, ask_price) -> H1 bid bars, UTC index."""
    t = t[(t.bid_price > 0) & (t.ask_price >= t.bid_price)].copy()
    t["spread"] = t.ask_price - t.bid_price
    g = t.set_index("timestamp").resample("1h")
    b = g["bid_price"].ohlc()
    b["spread"] = g["spread"].mean()
    b["open_bid"] = g["bid_price"].first()   # first real tick of the bar:
    b["open_ask"] = g["ask_price"].first()   # where an MT5 "new bar" EA gets filled
    b["ticks"] = g["bid_price"].count()
    return b[b.ticks > 0]


def build_symbol(sym: str) -> Path:
    files = sorted(glob.glob(str(REPO / sym / "year=*" / "month=*" / "*.parquet")))
    parts = []
    for i, f in enumerate(files, 1):
        parts.append(ticks_to_h1(pq.read_table(f, columns=["timestamp", "bid_price", "ask_price"]).to_pandas()))
        if i % 20 == 0:
            print(f"  {sym}: {i}/{len(files)} files")
    # A month can be split over several part files: merge overlapping hours.
    h1 = pd.concat(parts).groupby(level=0).agg(AGG).sort_index()
    BARS_DIR.mkdir(parents=True, exist_ok=True)
    out = BARS_DIR / f"{sym}_H1.csv.gz"
    h1.to_csv(out, float_format="%.5f")
    print(f"{sym}: {len(h1)} H1 bars {h1.index[0]} -> {h1.index[-1]} -> {out.relative_to(REPO)}")
    return out


def to_server(idx_utc: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """UTC timestamps -> MT5 server clock (naive)."""
    st = json.loads(SPEC_PATH.read_text())["server_time"]
    wall = idx_utc.tz_localize("UTC").tz_convert(st["base_tz"]).tz_localize(None)
    return wall + pd.Timedelta(hours=st["offset_hours"])


def load_h1_utc(sym: str) -> pd.DataFrame:
    h1 = pd.read_csv(BARS_DIR / f"{sym}_H1.csv.gz", index_col=0, parse_dates=True)
    live = BARS_DIR / f"{sym}_H1_live.csv.gz"  # appended by engine.livefeed
    if live.exists():
        lv = pd.read_csv(live, index_col=0, parse_dates=True)
        h1 = pd.concat([h1, lv[lv.index > h1.index[-1]]])
    return h1


def load_bars(sym: str, tf: str = "H1") -> pd.DataFrame:
    """Bars indexed in server time, with `utc` = UTC start of each bar."""
    h1 = load_h1_utc(sym)
    h1["utc"] = h1.index
    h1.index = to_server(h1.index)
    h1.index.name = "server_time"
    if tf == "H1":
        return h1
    out = h1.resample(TF_RULES[tf]).agg({**AGG, "utc": "first"})
    return out.dropna(subset=["close"])


def available_symbols() -> list[str]:
    return sorted(p.name.replace("_H1.csv.gz", "") for p in BARS_DIR.glob("*_H1.csv.gz") if "_live" not in p.name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    a = ap.parse_args()
    for s in a.symbols or tick_symbols():
        build_symbol(s)
