"""Bring price bars up to date from Dukascopy (the same source as the repo's tick data).

Downloads hourly tick files (bi5 = LZMA-compressed 20-byte records) for every
hour after the last cached bar, builds H1 bars (mid OHLC, mean spread, first
bid/ask) and appends them to engine/data/bars/<SYM>_H1_live.csv.gz.

Needs outbound HTTPS to datafeed.dukascopy.com. In a Claude cloud session that
host must be on the environment's allowed hosts list.

Usage:
    python -m engine.livefeed                 # all cached symbols
    python -m engine.livefeed --symbols XAUUSD --max-hours 48
"""
from __future__ import annotations

import argparse
import lzma
import struct
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import bars

DUKA = {"XAUUSD": ("XAUUSD", 1000.0), "US500": ("USA500IDXUSD", 1000.0)}
URL = "https://datafeed.dukascopy.com/datafeed/{inst}/{y:04d}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"


def fetch_hour(sym: str, hour: datetime) -> pd.DataFrame:
    inst, scale = DUKA[sym]
    url = URL.format(inst=inst, y=hour.year, m=hour.month - 1, d=hour.day, h=hour.hour)  # month is 0-based
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return pd.DataFrame()
            time.sleep(2 ** attempt)
        except urllib.error.URLError:
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"could not fetch {url}")
    if not raw:
        return pd.DataFrame()
    data = lzma.decompress(raw)
    rec = np.frombuffer(data, dtype=np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"),
                                              ("av", ">f4"), ("bv", ">f4")]))
    ts = pd.Timestamp(hour.replace(tzinfo=None)) + pd.to_timedelta(rec["ms"].astype(np.int64), unit="ms")
    return pd.DataFrame({"timestamp": ts, "bid_price": rec["bid"] / scale, "ask_price": rec["ask"] / scale})


def _to_bar(t: pd.DataFrame, hour: datetime) -> dict | None:
    t = t[(t.bid_price > 0) & (t.ask_price >= t.bid_price)]
    if t.empty:
        return None
    mid = (t.bid_price + t.ask_price) / 2
    return {"timestamp": pd.Timestamp(hour.replace(tzinfo=None)), "open": mid.iloc[0], "high": mid.max(),
            "low": mid.min(), "close": mid.iloc[-1], "spread": (t.ask_price - t.bid_price).mean(),
            "open_bid": t.bid_price.iloc[0], "open_ask": t.ask_price.iloc[0], "ticks": len(t)}


def update(sym: str, max_hours: int = 24 * 200) -> int:
    live = bars.BARS_DIR / f"{sym}_H1_live.csv.gz"
    last = bars.load_bars(sym, "H1").index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hours = [last + timedelta(hours=i) for i in range(1, max_hours + 1) if last + timedelta(hours=i) < now]
    new = []
    for i, h in enumerate(hours):
        if h.weekday() == 5:  # Saturday: market closed
            continue
        b = _to_bar(fetch_hour(sym, h), h)
        if b:
            new.append(b)
        if i and i % 200 == 0:
            print(f"  {sym}: {i}/{len(hours)} hours")
    if new:
        df = pd.DataFrame(new).set_index("timestamp")
        if live.exists():
            old = pd.read_csv(live, index_col=0, parse_dates=True)
            df = pd.concat([old, df])
            df = df[~df.index.duplicated(keep="last")].sort_index()
        df.to_csv(live, float_format="%.5f")
    print(f"{sym}: +{len(new)} bars, last {new[-1]['timestamp'] if new else last}")
    return len(new)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--max-hours", type=int, default=24 * 200)
    a = ap.parse_args()
    for s in a.symbols or bars.available_symbols():
        update(s, a.max_hours)
