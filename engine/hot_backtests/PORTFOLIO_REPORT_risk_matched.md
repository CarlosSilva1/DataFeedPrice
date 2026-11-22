# Portfolio report (2026-11-22T03:17:41Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **risk_matched**. MT5-style simulation: bid bars on the server clock, money account with real lots, ask/bid fills with slippage, commission, swap with triple day; portfolio combos re-verified on real ticks with the live signal delay.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|trend_pullback|D1 | `{"trend": 100, "n": 2, "lo": 10, "mode": "long"}` | **30.0** | 3.0x | 104.3 | 12.0 | 11.1 | 1.08 | 1.61 | 44 | 77 | 3.98 |
| XAUUSD|trend_ema|H4 | `{"n": 50, "mode": "long"}` | **24.42** | 1.63x | 141.6 | 102.6 | 22.4 | 1.04 | 1.61 | 290 | 24 | 1.74 |
| XAUUSD|ma_cross|H4 | `{"fast": 10, "slow": 50, "mode": "long"}` | **24.37** | 1.6x | 137.9 | 102.6 | 26.7 | 1.03 | 1.30 | 96 | 30 | 2.25 |
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **21.21** | 2.71x | 185.0 | 12.0 | 31.6 | 1.00 | 2.14 | 73 | 75 | 3.44 |

Per-combo numbers are the combo alone on the full deposit at its leverage.

## One account trading all combos (what the bot does)

- Deposit 10,000 -> final equity 24,126 (net 141.3%, CAGR 19.3%)
- Max drawdown 15.2%, Sharpe 1.54, profit factor 2.49, 503 trades, win rate 37%
- Max leverage used 2.27x, cash 0.0%
- Buy & hold of the same assets at the same weights: 47.2%, max DD 26.4%
- Entries skipped because the lot was below the broker minimum: {'US500|rsi_reversion|D1': '0/73', 'US500|trend_pullback|D1': '0/44', 'XAUUSD|ma_cross|H4': '0/96', 'XAUUSD|trend_ema|H4': '0/290'}
- Period 2021-05-24 -> 2026-05-25 (server time)

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 33.5 | 12.1 | 36.6 | outlier: only 5% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | -17.8 | 12.1 | 43.6 | does not beat buy & hold (-17.8% vs 12.1%); outlier: falls apart out-of-sample (Sharpe 0.22 -> -0.62); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|donchian|H4 | -5.7 | 12.1 | 38.6 | does not beat buy & hold (-5.7% vs 12.1%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|macd|H4 | -4.7 | 12.1 | 35.2 | does not beat buy & hold (-4.7% vs 12.1%); outlier: falls apart out-of-sample (Sharpe 0.13 -> -0.01); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|rsi_reversion|H4 | 50.7 | 12.1 | 40.4 | outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 69.9 | 12.1 | 31.3 | outlier: only 38% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 17.6 | 12.1 | 27.6 | outlier: only 0% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | -6.3 | 12.0 | 39.6 | does not beat buy & hold (-6.3% vs 12.0%); outlier: only 9% of parameter sets profitable (curve fit) |
| US500|trend_ema|D1 | -7.1 | 12.0 | 46.0 | does not beat buy & hold (-7.1% vs 12.0%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 0.7 | 12.0 | 37.1 | does not beat buy & hold (0.7% vs 12.0%); outlier: only 17% of parameter sets profitable (curve fit) |
| US500|macd|D1 | -28.1 | 12.0 | 44.6 | does not beat buy & hold (-28.1% vs 12.0%); outlier: falls apart out-of-sample (Sharpe -0.19 -> -0.11); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|D1 | 12.7 | 12.0 | 29.2 | outlier: only 19 trades; outlier: falls apart out-of-sample (Sharpe 0.54 -> -0.33) |
| XAUUSD|donchian|H4 | 67.4 | 102.6 | 28.8 | does not beat buy & hold (67.4% vs 102.6%); outlier: only 33% of parameter sets profitable (curve fit) |
| XAUUSD|macd|H4 | 69.3 | 102.6 | 43.4 | does not beat buy & hold (69.3% vs 102.6%); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|rsi_reversion|H4 | 42.8 | 102.6 | 33.2 | does not beat buy & hold (42.8% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|H4 | 10.8 | 102.6 | 36.3 | does not beat buy & hold (10.8% vs 102.6%); outlier: only 25% of parameter sets profitable (curve fit) |
| XAUUSD|trend_pullback|H4 | -47.6 | 102.6 | 48.4 | does not beat buy & hold (-47.6% vs 102.6%); outlier: falls apart out-of-sample (Sharpe -0.37 -> -1.05); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|ma_cross|D1 | 85.9 | 102.6 | 19.8 | does not beat buy & hold (85.9% vs 102.6%) |
| XAUUSD|trend_ema|D1 | 95.5 | 102.6 | 22.3 | does not beat buy & hold (95.5% vs 102.6%); outlier: profit factor 5.01 > 5.0 |
| XAUUSD|donchian|D1 | 33.3 | 102.6 | 22.5 | does not beat buy & hold (33.3% vs 102.6%) |
| XAUUSD|macd|D1 | 40.1 | 102.6 | 25.1 | does not beat buy & hold (40.1% vs 102.6%) |
| XAUUSD|rsi_reversion|D1 | -13.7 | 102.6 | 46.2 | does not beat buy & hold (-13.7% vs 102.6%); outlier: falls apart out-of-sample (Sharpe 0.21 -> -0.43); outlier: only 31% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|D1 | 65.9 | 102.6 | 26.8 | does not beat buy & hold (65.9% vs 102.6%) |
| XAUUSD|trend_pullback|D1 | 10.4 | 102.6 | 35.0 | does not beat buy & hold (10.4% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |

Past results do not predict future returns. Not investment advice.
