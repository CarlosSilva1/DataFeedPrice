# Portfolio report (2026-11-22T01:35:27Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **risk_matched**. Execution: MT5-style (first tick of next bar, bid/ask, slippage, commission, swap); portfolio combos re-verified on real ticks with latency.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|trend_pullback|D1 | `{"trend": 100, "n": 2, "lo": 10, "mode": "long"}` | **29.05** | 3.0x | 120.1 | 32.8 | 8.0 | 1.26 | 1.51 | 50 | 82 | 4.22 |
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **15.47** | 2.14x | 97.8 | 32.8 | 24.0 | 0.79 | 1.04 | 83 | 73 | 2.31 |
| XAUUSD|ma_cross|D1 | `{"fast": 5, "slow": 50, "mode": "long"}` | **14.76** | 1.16x | 101.9 | 90.6 | 17.1 | 0.78 | 1.16 | 26 | 31 | 3.62 |
| XAUUSD|ma_cross|H4 | `{"fast": 10, "slow": 50, "mode": "long"}` | **14.17** | 1.33x | 112.5 | 90.6 | 23.8 | 0.93 | 1.18 | 93 | 33 | 2.15 |
| XAUUSD|trend_ema|H4 | `{"n": 50, "mode": "long"}` | **13.92** | 1.33x | 99.7 | 90.6 | 24.1 | 0.86 | 1.28 | 282 | 24 | 1.72 |
| US500|bollinger_reversion|D1 | `{"n": 20, "k": 2.0, "mode": "long"}` | **12.63** | 1.46x | 47.6 | 32.8 | 20.3 | 0.48 | 0.25 | 30 | 73 | 2.71 |

Cash: 0.0%

**Portfolio:** net 108.4% (CAGR 15.8%), max DD 7.8%, Sharpe 1.29. Buy & hold of the same assets at the same weights: 108.9%, max DD 18.8%. Period 2021-05-24 -> 2026-05-22.

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 60.1 | 32.8 | 25.5 | outlier: only 27% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | 38.0 | 32.8 | 26.0 | outlier: only 38% of parameter sets profitable (curve fit) |
| US500|donchian|H4 | 38.0 | 32.8 | 23.4 | outlier: only 17% of parameter sets profitable (curve fit) |
| US500|macd|H4 | 21.0 | 32.8 | 21.8 | does not beat buy & hold (21.0% vs 32.8%); outlier: falls apart out-of-sample (Sharpe 0.40 -> 0.07) |
| US500|rsi_reversion|H4 | 47.7 | 32.8 | 21.9 | outlier: only 19% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 36.4 | 32.8 | 25.4 | outlier: only 25% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 46.9 | 32.8 | 23.7 | outlier: only 6% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | -16.1 | 32.8 | 32.6 | does not beat buy & hold (-16.1% vs 32.8%); outlier: only 18 trades; outlier: falls apart out-of-sample (Sharpe 0.10 -> -0.56) |
| US500|trend_ema|D1 | 7.3 | 32.8 | 38.2 | does not beat buy & hold (7.3% vs 32.8%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 38.4 | 32.8 | 29.2 | outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|D1 | -0.5 | 32.8 | 28.2 | does not beat buy & hold (-0.5% vs 32.8%); outlier: falls apart out-of-sample (Sharpe 0.17 -> -0.18); outlier: only 12% of parameter sets profitable (curve fit) |
| XAUUSD|donchian|H4 | 56.1 | 90.6 | 29.2 | does not beat buy & hold (56.1% vs 90.6%) |
| XAUUSD|macd|H4 | 88.3 | 90.6 | 35.4 | does not beat buy & hold (88.3% vs 90.6%); outlier: only 12% of parameter sets profitable (curve fit) |
| XAUUSD|rsi_reversion|H4 | 26.0 | 90.6 | 31.7 | does not beat buy & hold (26.0% vs 90.6%); outlier: only 38% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|H4 | 6.8 | 90.6 | 31.7 | does not beat buy & hold (6.8% vs 90.6%); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|trend_pullback|H4 | -27.7 | 90.6 | 34.8 | does not beat buy & hold (-27.7% vs 90.6%); outlier: falls apart out-of-sample (Sharpe -0.27 -> -0.32); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|trend_ema|D1 | 83.2 | 90.6 | 26.6 | does not beat buy & hold (83.2% vs 90.6%) |
| XAUUSD|donchian|D1 | 51.8 | 90.6 | 19.2 | does not beat buy & hold (51.8% vs 90.6%) |
| XAUUSD|macd|D1 | 72.2 | 90.6 | 23.3 | does not beat buy & hold (72.2% vs 90.6%) |
| XAUUSD|rsi_reversion|D1 | -20.8 | 90.6 | 51.7 | does not beat buy & hold (-20.8% vs 90.6%); max drawdown 51.7% >= 50.0%; outlier: falls apart out-of-sample (Sharpe 0.17 -> -0.58); outlier: only 44% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|D1 | 15.9 | 90.6 | 40.8 | does not beat buy & hold (15.9% vs 90.6%) |
| XAUUSD|trend_pullback|D1 | 50.8 | 90.6 | 24.8 | does not beat buy & hold (50.8% vs 90.6%); outlier: only 25% of parameter sets profitable (curve fit) |

Backtests use mid prices with half the average spread paid per side plus 0.5 bp slippage. Past results do not predict future returns. Not investment advice.
