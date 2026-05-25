---
license: cc-by-4.0
language:
  - en
pretty_name: XAU/USD Tick Data 2021-2026
size_categories:
  - 100M<n<1B
task_categories:
  - time-series-forecasting
  - tabular-regression
tags:
  - finance
  - forex
  - gold
  - tick-data
  - xauusd
  - high-frequency
  - backtesting
configs:
  - config_name: default
    data_files:
      - split: train
        path: "year=*/month=*/*.parquet"
---

# XAU/USD Tick Data (May 2021 – May 2026)

Five years of tick-by-tick bid/ask quotes for **gold against the US dollar (XAU/USD)** at millisecond resolution. Suitable for backtesting high-frequency strategies, market-microstructure research, and time-series modeling.

## Dataset details

| | |
|---|---|
| **Instrument** | XAU/USD (spot gold) |
| **Period** | 2021-05-24 → 2026-05-24 |
| **Granularity** | Tick (millisecond timestamps) |
| **Rows** | ~hundreds of millions |
| **Format** | Apache Parquet (Snappy) |
| **Partitioning** | Hive-style by `year`/`month` |

## Schema

| Column | Type | Description |
|---|---|---|
| `timestamp` | `timestamp[ms]` | UTC tick time, millisecond precision |
| `bid_price` | `float64` | Best bid price in USD |
| `ask_price` | `float64` | Best ask price in USD |
| `bid_volume` | `float64` | Bid-side volume |
| `ask_volume` | `float64` | Ask-side volume |

## Layout

```
year=2021/
├── month=05/XAUUSD-2021-05-part0000.parquet
├── month=05/XAUUSD-2021-05-part0001.parquet
├── month=06/XAUUSD-2021-06-part0000.parquet
└── ...
year=2022/
└── ...
year=2026/
└── month=05/XAUUSD-2026-05-part000N.parquet
```

Hive partitioning lets you read a single month without scanning the rest:

```python
import pyarrow.dataset as ds
dataset = ds.dataset(".", partitioning="hive")
march_2024 = dataset.to_table(filter=(ds.field("year") == 2024) & (ds.field("month") == 3))
```

## Quick start

### Hugging Face `datasets` library

```python
from datasets import load_dataset

ds = load_dataset("CarlosSilva1/xauusd-ticks", split="train", streaming=True)
for row in ds.take(5):
    print(row)
```

Streaming mode avoids downloading the whole dataset upfront.

### Direct Parquet with pandas

```python
import pandas as pd

# Read a single month part
df = pd.read_parquet(
    "https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks/resolve/main/"
    "year=2024/month=03/XAUUSD-2024-03-part0001.parquet"
)
print(df.head())
```

### Bulk download via `huggingface_hub`

```python
from huggingface_hub import snapshot_download

local_path = snapshot_download(
    repo_id="CarlosSilva1/xauusd-ticks",
    repo_type="dataset",
)
print("Downloaded to:", local_path)
```

## Typical use cases

- Backtesting intraday and high-frequency trading strategies
- Studying bid-ask spread dynamics for gold
- Training time-series forecasting models (transformers, LSTM, N-BEATS, etc.)
- Volatility and market microstructure research
- Calibrating execution simulators

## Source and provenance

Aggregated tick feed reconstructed from broker data for personal backtesting research. Timestamps are in UTC. Prices reflect the broker feed at the time of capture and may differ slightly from other venues.

## License

[Creative Commons Attribution 4.0 (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/).

You may use, share and adapt the data, including commercially, **provided you give appropriate credit**. Citation suggestion:

```
Silva, C. (2026). XAU/USD Tick Data (May 2021 – May 2026)
[Data set]. Hugging Face. https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks
```

## Disclaimer

This dataset is provided **as-is for research and educational purposes**. It is **not** investment advice. Past price action is not indicative of future performance. The author is not responsible for any losses incurred from strategies developed using this data.
