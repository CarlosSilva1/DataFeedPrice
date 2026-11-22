"""Bring price bars up to date from Dukascopy (the same source as the repo's tick data).

Downloads hourly tick files (bi5 = LZMA-compressed 20-byte records) for every
hour after the last cached bar, builds H1 bid bars (same as engine.bars) and appends them to engine/data/bars/<SYM>_H1_live.csv.gz.

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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import bars

DUKA = {"XAUUSD": ("XAUUSD", 1000.0), "US500": ("USA500IDXUSD", 1000.0)}
URL = "https://datafeed.dukascopy.com/datafeed/{inst}/{y:04d}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"


def fetch_hour(sym: str, hour: datetime) -> pd.DataFrame:
    inst, scale = DUKA[sym]
    url = URL.format(inst=inst, y=hour.year, m=hour.month - 1, d=hour.day, h=hour.hour)  # month is 0-based
    for attempt in range(15):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return pd.DataFrame()
            time.sleep(min(1.5 ** attempt, 30))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(min(1.5 ** attempt, 30))
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
    if t.empty:
        return None
    b = bars.ticks_to_h1(t)            # same bid-bar construction as the historical bars
    if b.empty:
        return None
    return {"timestamp": pd.Timestamp(hour.replace(tzinfo=None)), **b.iloc[0].to_dict()}


def _save(live, new: list[dict]) -> None:
    df = pd.DataFrame(new).set_index("timestamp")
    if live.exists():
        old = pd.read_csv(live, index_col=0, parse_dates=True)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_csv(live, float_format="%.5f")


def update(sym: str, max_hours: int = 24 * 200, chunk: int = 100) -> int:
    """Fetch every missing hour in order, saving after each chunk so an
    interrupted run keeps its progress and the next run resumes from there."""
    live = bars.BARS_DIR / f"{sym}_H1_live.csv.gz"
    last = bars.load_h1_utc(sym).index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hours = [last + timedelta(hours=i) for i in range(1, max_hours + 1) if last + timedelta(hours=i) < now]
    # Market closed: Friday 22:00 UTC -> Sunday 21:00 UTC
    hours = [h for h in hours if not (h.weekday() == 5 or (h.weekday() == 4 and h.hour >= 22)
                                      or (h.weekday() == 6 and h.hour < 21))]

    def one(h):
        try:
            return _to_bar(fetch_hour(sym, h), h)
        except RuntimeError as e:
            return e

    total, last_ts = 0, last
    with ThreadPoolExecutor(max_workers=3) as ex:
        for k in range(0, len(hours), chunk):
            part = hours[k:k + chunk]
            new, failed = [], None
            for h, b in zip(part, ex.map(one, part)):
                if isinstance(b, RuntimeError):  # keep everything before the gap; resume here next run
                    failed = (h, b)
                    break
                if b:
                    new.append(b)
            if new:
                _save(live, new)
                total += len(new)
                last_ts = new[-1]["timestamp"]
            print(f"  {sym}: {min(k + chunk, len(hours))}/{len(hours)} hours, last bar {last_ts}", flush=True)
            if failed:
                print(f"  {sym}: {failed[1]}; stopping at {failed[0]}")
                break
    print(f"{sym}: +{total} bars, last {last_ts}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--max-hours", type=int, default=24 * 200)
    a = ap.parse_args()
    for s in a.symbols or bars.available_symbols():
        update(s, a.max_hours)
