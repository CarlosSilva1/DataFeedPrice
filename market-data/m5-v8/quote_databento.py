import json
from pathlib import Path

import databento as db

ROOT = Path(__file__).resolve().parent
SYMBOLS = [s.strip() for s in (ROOT / "symbols-168.txt").read_text().splitlines() if s.strip()]

DATASET = "XNAS.ITCH"
SCHEMA = "ohlcv-1m"
END = "2026-08-15"
PERIODS = {
    "full_2018_2026": "2018-05-01",
    "2020_2026": "2020-01-01",
    "2023_2026": "2023-01-01",
}

client = db.Historical()

result = {
    "dataset": DATASET,
    "schema": SCHEMA,
    "end_exclusive": END,
    "symbol_count": len(SYMBOLS),
    "symbols": SYMBOLS,
    "dataset_range": client.metadata.get_dataset_range(DATASET),
    "quotes": {},
}

for label, start in PERIODS.items():
    kwargs = dict(
        dataset=DATASET,
        symbols=SYMBOLS,
        schema=SCHEMA,
        start=start,
        end=END,
        stype_in="raw_symbol",
    )
    result["quotes"][label] = {
        "start": start,
        "end_exclusive": END,
        "cost_usd": client.metadata.get_cost(**kwargs),
        "billable_size_bytes": client.metadata.get_billable_size(**kwargs),
        "record_count": client.metadata.get_record_count(**kwargs),
    }

out = ROOT / "databento_quote.json"
out.write_text(json.dumps(result, indent=2, default=str) + "\n")
print(json.dumps(result, indent=2, default=str))
print(f"\nSaved quote to {out}")
