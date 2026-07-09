# Wayward EA — tick-level backtester

A standalone Python harness that replays the repository's real bid/ask tick data
through the Wayward EA's exact logic, engineered to **approximate the MT5 Strategy
Tester on "Every tick"**. Use it to sanity-check the EA before running it in
MetaTrader.

## What it reproduces (MT5 fidelity)

- **Bars from Bid** on the working timeframe (MT5 default chart pricing).
- **Indicators recomputed on the *forming* bar (index 0) every tick** — exactly
  what the EA reads via `CopyBuffer(..., 0, ...)`:
  - Bollinger = `SMA(close,P) ± dev · populationStdDev(close,P)`
  - RSI = Wilder's SMMA smoothing (seeded by SMA of the first `P` changes)
  - ATR(1000) = Wilder's smoothing of True Range (seeded by SMA of first `P` TRs)
  - Completed-bar recursion state is carried forward; the forming bar's close is
    the running Bid and its high/low are the running Bid high/low.
- **Stop-order fills** on ask (buy) / bid (sell) crossings, taking the crossing
  price on gaps (adverse). **Stop-loss** fills at market (worse of SL / market);
  **take-profit** at the level.
- One position **or** one pending order at a time, pending-trailing, position
  trailing stop, session window, pending-age expiry, and risk-based lot sizing
  clamped to broker `MinLot/MaxLot/LotStep` — all mirroring the EA.

## Approximations / omitted (be aware)

- No swap or commission (add per-lot cost and results worsen).
- No margin stop-out, so a wiped account can show a negative balance.
- Broker `StopLevel` set to 0; slippage modelled only via the crossing price.
- Spread cap raised from the EA default (10 points — impossible on 3-digit gold)
  to a realistic per-instrument value.

## Usage

```bash
pip install numpy pandas pyarrow numba

# XAUUSD, M5, first half of 2025 (default)
python backtest.py

# US500, M5
python backtest.py --symbol US500 --glob 'US500/year=2025/month=0[1-6]/*.parquet'

# XAUUSD, M1
python backtest.py --symbol XAUUSD --tf 1 --glob 'XAUUSD/year=2025/month=0[1-6]/*.parquet'
```

Edit the `P` dict at the top of `backtest.py` to change strategy parameters; it
writes an `equity.csv` (one row per closed trade) and prints a summary.

## Results (Jan–Jun 2025, $1,000 deposit, 1% risk)

| Run | Trades | Win rate | Profit factor | Net | Max DD |
|---|---|---|---|---|---|
| XAUUSD M5 | 481 | 73.4% | 0.56 | −$277.51 (−27.8%) | 28.1% |
| US500 M5  | 945 | 68.3% | 0.62 | −$462.89 (−46.3%) | 47.2% |
| XAUUSD M1 | 1,547 | 53.5% | 0.26 | −$1,421.10 (−142.1%) | 142.1% |

**Takeaway:** as literally coded, the EA is a net loser on these instruments. Win
rates are high but wins are tiny (trailed at `0.2×ATR`) while losses run to the
full `2×ATR` stop, and the Bollinger-middle take-profit is essentially never
reached (1 TP exit across all 1,973 trades). Spread is a heavy drag, dominating
entirely on M1. The source strategy was tuned on USDJPY (5-digit, ~1-point
spread); it does not transfer to gold / indices without re-tuning.

*Not investment advice.*
