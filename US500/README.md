---
license: cc-by-4.0
language:
  - en
pretty_name: US500 (S&P 500) Tick Data 2021-2026
size_categories:
  - 10M<n<100M
task_categories:
  - time-series-forecasting
  - tabular-regression
tags:
  - finance
  - indices
  - sp500
  - us500
  - tick-data
  - high-frequency
  - backtesting
configs:
  - config_name: default
    data_files:
      - split: train
        path: "year=*/month=*/*.parquet"
---

# US500 (S&P 500) Tick Data (May 2021 – May 2026)

Five years of tick-by-tick bid/ask quotes for the **S&P 500 index CFD** at millisecond resolution. Sourced from Dukascopy via Tickstory.

## Dataset details

| | |
|---|---|
| **Instrument** | US500 (S&P 500 Index CFD) |
| **Period** | 2021-05-24 → 2026-05-24 |
| **Granularity** | Tick (millisecond timestamps) |
| **Rows** | ~90 million |
| **Format** | Apache Parquet (Snappy) |
| **Partitioning** | Hive-style by `year`/`month` |

## Schema

| Column | Type | Description |
|---|---|---|
| `timestamp` | `timestamp[ms]` | UTC tick time, millisecond precision |
| `bid_price` | `float64` | Best bid price (index points) |
| `ask_price` | `float64` | Best ask price (index points) |
| `bid_volume` | `float64` | Bid-side volume |
| `ask_volume` | `float64` | Ask-side volume |

## Quick start

```python
from datasets import load_dataset
ds = load_dataset("CarlosSilva1/us500-ticks", split="train", streaming=True)
for row in ds.take(5):
    print(row)
```

Or with pandas:

```python
import pandas as pd
df = pd.read_parquet(
    "https://huggingface.co/datasets/CarlosSilva1/us500-ticks/resolve/main/"
    "year=2024/month=03/US500-2024-03-part0001.parquet"
)
print(df.head())
```

## Typical use cases

- Backtesting intraday S&P 500 strategies
- Correlation analysis vs. gold (XAU/USD), bonds, VIX
- Market microstructure research
- Volatility regime detection
- Pair trading between US indices

## Related datasets

- [CarlosSilva1/xauusd-ticks](https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks) - Gold/USD tick data, same period

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Provided as-is for research and educational purposes. Not investment advice.
