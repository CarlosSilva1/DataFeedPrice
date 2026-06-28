# tools

Utilitários para usar os ticks deste repositório.

## `parquet_to_mt4_csv.py`

Converte os Parquet (XAUUSD / US500) para CSV de tick no formato que o
MetaTrader 4 / Tick Data Suite importam para backtest com 99% de qualidade.

```bash
pip install pandas pyarrow

# CSV único de um intervalo
python tools/parquet_to_mt4_csv.py --instrument XAUUSD \
    --from 2024-01-01 --to 2024-03-31 --out XAUUSD_2024Q1.csv

# Um CSV por mês
python tools/parquet_to_mt4_csv.py --instrument US500 \
    --from 2023-01-01 --to 2023-12-31 --out-dir ./mt4_csv --split month
```

Saída: `YYYY.MM.DD HH:MM:SS,bid,ask,volume` (UTC).

O passo a passo completo de como importar no MT4 está em
[`../GUIA-BACKTEST-MT4.md`](../GUIA-BACKTEST-MT4.md).
