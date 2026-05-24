# DataFeedPrice

Dados de tick XAU/USD para backtesting (2021-05-24 a 2026-05-24).

## Estrutura

- `year=YYYY/month=MM/XAUUSD-YYYY-MM-partNNNN.parquet` - arquivos Parquet particionados
- Total: ~286M ticks, 2.47 GB
- Schema: `timestamp[ms]`, `bid_price`, `ask_price`, `bid_volume`, `ask_volume`

## Uso programatico

```python
import pyarrow.dataset as ds
dataset = ds.dataset(".", partitioning="hive", format="parquet", exclude_invalid_files=True)
table = dataset.to_table(filter=(ds.field("year") == 2024) & (ds.field("month") == 3))
```

Tambem disponivel via Hugging Face: https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks

## Acesso pelo Claude (Cowork)

Em qualquer sessao do Claude:
```bash
git clone --depth 1 https://github.com/CarlosSilva1/DataFeedPrice.git
```
Depois pyarrow le diretamente do diretorio clonado.
