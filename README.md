# DataFeedPrice

Tick-by-tick price data for backtesting. Organized as one subfolder per instrument.

## Available instruments

| Symbol | Description | Ticks | Size | Period |
|---|---|---|---|---|
| [XAUUSD](./XAUUSD) | Gold vs USD | 286M | 2.47 GB | 2021-05-24 â†’ 2026-05-24 |
| [US500](./US500) | S&P 500 Index CFD | 90M | 0.87 GB | 2021-05-24 â†’ 2026-05-24 |

## Schema (all instruments)

Each `.parquet` file has:
- `timestamp` - timestamp[ms], UTC
- `bid_price`, `ask_price` - float64
- `bid_volume`, `ask_volume` - float64

Files are organized in Hive-style partitions: `<SYMBOL>/year=YYYY/month=MM/<SYMBOL>-YYYY-MM-partNNNN.parquet`

## Usage

### Read a single month locally

```python
import pyarrow.parquet as pq
df = pq.read_table('XAUUSD/year=2024/month=03/XAUUSD-2024-03-part0001.parquet').to_pandas()
```

### Read an entire instrument with pyarrow.dataset

```python
import pyarrow.dataset as ds
xau = ds.dataset('XAUUSD', partitioning='hive', format='parquet', exclude_invalid_files=True)
table = xau.to_table(filter=(ds.field('year') == 2024) & (ds.field('month') == 3))
```

### Clone only the part you need (recommended for big subsets)

```bash
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/CarlosSilva1/DataFeedPrice.git
cd DataFeedPrice
git config core.sparseCheckout true
echo 'XAUUSD/year=2024/month=03/*' > .git/info/sparse-checkout
git checkout main
```

## Mirror on Hugging Face

Each instrument is also published as a separate Hugging Face dataset for the ML/quant community:

- https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks
- https://huggingface.co/datasets/CarlosSilva1/us500-ticks

## License

CC-BY-4.0. Provided as-is for research/educational purposes. Not investment advice.
