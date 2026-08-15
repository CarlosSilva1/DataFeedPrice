#!/usr/bin/env python3
"""Quote Databento historical OHLCV-1m requests without downloading data."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

DATASET = "XNAS.ITCH"
SCHEMA = "ohlcv-1m"
DEFAULT_END = "2026-08-16"
DEFAULT_PERIODS = {
    "full_2018_2026": "2018-05-01",
    "2020_2026": "2020-01-01",
    "2023_2026": "2023-01-01",
}

def load_symbols(path: Path) -> list[str]:
    syms = [x.strip() for x in path.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    return list(dict.fromkeys(syms))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=Path, required=True)
    ap.add_argument('--end', default=DEFAULT_END)
    ap.add_argument('--out', type=Path, default=Path('databento_quote.json'))
    args = ap.parse_args()
    if not os.environ.get('DATABENTO_API_KEY'):
        raise SystemExit('DATABENTO_API_KEY is not set in the environment')
    import databento as db
    symbols = load_symbols(args.symbols)
    client = db.Historical()
    result = {'dataset': DATASET, 'schema': SCHEMA, 'end_exclusive': args.end, 'symbol_count': len(symbols), 'quotes': {}}
    for label, start in DEFAULT_PERIODS.items():
        kw = dict(dataset=DATASET, symbols=symbols, schema=SCHEMA, start=start, end=args.end, stype_in='raw_symbol')
        result['quotes'][label] = {
            'start': start,
            'cost_usd': float(client.metadata.get_cost(**kw)),
            'billable_size_bytes': int(client.metadata.get_billable_size(**kw)),
            'record_count': int(client.metadata.get_record_count(**kw)),
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
