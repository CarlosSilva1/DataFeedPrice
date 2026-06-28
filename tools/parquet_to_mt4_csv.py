#!/usr/bin/env python3
"""
parquet_to_mt4_csv.py
=====================

Converte os ticks em Parquet deste repositorio (XAUUSD / US500) para CSV de tick
no formato que o MetaTrader 4 / Tick Data Suite consegue importar para um
backtest com qualidade de modelagem de 99%.

Formato de saida (uma linha por tick):

    YYYY.MM.DD HH:MM:SS,<bid>,<ask>,<volume>

Esse e o formato de "tick data CSV" aceito pelo Tick Data Suite (TDS) e por
conversores CSV->FXT. As datas usam pontos (YYYY.MM.DD), que e o padrao do MT4.
O timestamp ja esta em UTC no dataset.

Exemplos
--------
# Um instrumento, intervalo de datas, um unico CSV:
    python tools/parquet_to_mt4_csv.py --instrument XAUUSD \
        --from 2024-01-01 --to 2024-03-31 --out XAUUSD_2024Q1.csv

# Quebrar em um arquivo por mes (recomendado p/ TDS, arquivos menores):
    python tools/parquet_to_mt4_csv.py --instrument US500 \
        --from 2023-01-01 --to 2023-12-31 --out-dir ./mt4_csv --split month

Dependencias:  pip install pandas pyarrow
"""
import argparse
import os
import sys
from datetime import datetime

try:
    import pandas as pd
    import pyarrow.dataset as ds
    import pyarrow.compute as pc
except ImportError:
    sys.exit("Faltam dependencias. Rode:  pip install pandas pyarrow")


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def month_range(start: datetime, end: datetime):
    """Lista de tuplas (ano, mes) entre start e end, inclusive."""
    y, m = start.year, start.month
    out = []
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def load_month(instrument: str, year: int, month: int) -> pd.DataFrame:
    """Le todos os parquet de um mes (uma ou varias partes) ja ordenados."""
    folder = os.path.join(REPO_ROOT, instrument, f"year={year}", f"month={month:02d}")
    if not os.path.isdir(folder):
        return pd.DataFrame()
    dataset = ds.dataset(folder, format="parquet")
    table = dataset.to_table(columns=["timestamp", "bid_price", "ask_price",
                                      "bid_volume", "ask_volume"])
    df = table.to_pandas()
    if df.empty:
        return df
    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return df


def format_block(df: pd.DataFrame, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Filtra pelo intervalo e formata as colunas no padrao MT4."""
    df = df[(df["timestamp"] >= date_from) & (df["timestamp"] <= date_to)].copy()
    if df.empty:
        return df
    # Volume do tick: usa o volume do bid; cai para 1 quando ausente/zero.
    vol = df["bid_volume"].fillna(0)
    df["volume"] = vol.where(vol > 0, 1.0)
    df["dt"] = df["timestamp"].dt.strftime("%Y.%m.%d %H:%M:%S")
    return df[["dt", "bid_price", "ask_price", "volume"]]


def write_csv(block: pd.DataFrame, path: str, header: bool):
    block.to_csv(path, index=False, header=header,
                 columns=["dt", "bid_price", "ask_price", "volume"],
                 float_format="%.5f")


def main():
    ap = argparse.ArgumentParser(description="Parquet de ticks -> CSV para MT4 / Tick Data Suite")
    ap.add_argument("--instrument", required=True, choices=["XAUUSD", "US500"])
    ap.add_argument("--from", dest="date_from", required=True, help="data inicial YYYY-MM-DD (UTC)")
    ap.add_argument("--to", dest="date_to", required=True, help="data final YYYY-MM-DD (UTC, inclusive)")
    ap.add_argument("--out", help="arquivo CSV unico de saida")
    ap.add_argument("--out-dir", help="pasta de saida quando --split for usado")
    ap.add_argument("--split", choices=["none", "month"], default="none",
                    help="'month' gera um CSV por mes dentro de --out-dir")
    ap.add_argument("--no-header", action="store_true", help="omite a linha de cabecalho")
    args = ap.parse_args()

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    if date_to < date_from:
        sys.exit("--to nao pode ser anterior a --from")

    months = month_range(date_from, date_to)
    header = not args.no_header
    total = 0

    if args.split == "month":
        if not args.out_dir:
            sys.exit("--split month exige --out-dir")
        os.makedirs(args.out_dir, exist_ok=True)
        for (y, m) in months:
            df = load_month(args.instrument, y, m)
            if df.empty:
                print(f"  {y}-{m:02d}: sem dados, pulando")
                continue
            block = format_block(df, date_from, date_to)
            if block.empty:
                continue
            path = os.path.join(args.out_dir, f"{args.instrument}_{y}_{m:02d}.csv")
            write_csv(block, path, header)
            total += len(block)
            print(f"  {y}-{m:02d}: {len(block):>9,} ticks -> {path}")
    else:
        if not args.out:
            sys.exit("modo padrao exige --out (ou use --split month com --out-dir)")
        wrote_header = False
        # escreve incrementalmente para nao carregar anos inteiros na memoria
        with open(args.out, "w", newline="") as fh:
            for (y, m) in months:
                df = load_month(args.instrument, y, m)
                if df.empty:
                    print(f"  {y}-{m:02d}: sem dados, pulando")
                    continue
                block = format_block(df, date_from, date_to)
                if block.empty:
                    continue
                block.to_csv(fh, index=False, header=(header and not wrote_header),
                             columns=["dt", "bid_price", "ask_price", "volume"],
                             float_format="%.5f")
                wrote_header = True
                total += len(block)
                print(f"  {y}-{m:02d}: {len(block):>9,} ticks")
        print(f"\nArquivo: {args.out}")

    print(f"\nTotal: {total:,} ticks convertidos.")
    if total == 0:
        print("ATENCAO: 0 ticks. Confira o intervalo de datas e o instrumento.")


if __name__ == "__main__":
    main()
