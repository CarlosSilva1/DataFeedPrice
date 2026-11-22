# Portfolio report (2026-11-22T01:35:38Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **absolute**. Execution: MT5-style (first tick of next bar, bid/ask, slippage, commission, swap); portfolio combos re-verified on real ticks with latency.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **30.0** | 1.0x | 40.1 | 32.8 | 11.7 | 0.79 | 1.04 | 83 | 73 | 2.36 |

Cash: 70.0%

**Portfolio:** net 11.0% (CAGR 2.1%), max DD 3.6%, Sharpe 0.73. Buy & hold of the same assets at the same weights: 20.7%, max DD 8.1%. Period 2021-05-24 -> 2026-05-22.

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 35.3 | 32.8 | 16.0 | outlier: only 27% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | 23.1 | 32.8 | 15.7 | does not beat buy & hold (23.1% vs 32.8%); outlier: only 38% of parameter sets profitable (curve fit) |
| US500|donchian|H4 | 19.4 | 32.8 | 11.9 | does not beat buy & hold (19.4% vs 32.8%); outlier: only 17% of parameter sets profitable (curve fit) |
| US500|macd|H4 | 16.5 | 32.8 | 16.2 | does not beat buy & hold (16.5% vs 32.8%); outlier: falls apart out-of-sample (Sharpe 0.40 -> 0.07) |
| US500|rsi_reversion|H4 | 27.1 | 32.8 | 13.0 | does not beat buy & hold (27.1% vs 32.8%); outlier: only 19% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 21.0 | 32.8 | 14.4 | does not beat buy & hold (21.0% vs 32.8%); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 16.7 | 32.8 | 9.0 | does not beat buy & hold (16.7% vs 32.8%); outlier: only 6% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | -16.2 | 32.8 | 32.6 | does not beat buy & hold (-16.2% vs 32.8%); outlier: only 18 trades; outlier: falls apart out-of-sample (Sharpe 0.10 -> -0.56) |
| US500|trend_ema|D1 | 6.3 | 32.8 | 25.6 | does not beat buy & hold (6.3% vs 32.8%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 19.9 | 32.8 | 15.2 | does not beat buy & hold (19.9% vs 32.8%); outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|D1 | 1.5 | 32.8 | 17.3 | does not beat buy & hold (1.5% vs 32.8%); outlier: falls apart out-of-sample (Sharpe 0.17 -> -0.18); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|D1 | 32.6 | 32.8 | 14.2 | does not beat buy & hold (32.6% vs 32.8%) |
| US500|trend_pullback|D1 | 31.1 | 32.8 | 2.7 | does not beat buy & hold (31.1% vs 32.8%) |
| XAUUSD|ma_cross|H4 | 78.7 | 90.6 | 18.2 | does not beat buy & hold (78.7% vs 90.6%) |
| XAUUSD|trend_ema|H4 | 70.6 | 90.6 | 18.4 | does not beat buy & hold (70.6% vs 90.6%) |
| XAUUSD|donchian|H4 | 39.6 | 90.6 | 21.8 | does not beat buy & hold (39.6% vs 90.6%) |
| XAUUSD|macd|H4 | 59.1 | 90.6 | 26.3 | does not beat buy & hold (59.1% vs 90.6%); outlier: only 12% of parameter sets profitable (curve fit) |
| XAUUSD|rsi_reversion|H4 | 12.4 | 90.6 | 14.8 | does not beat buy & hold (12.4% vs 90.6%); outlier: only 38% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|H4 | 5.4 | 90.6 | 17.9 | does not beat buy & hold (5.4% vs 90.6%); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|trend_pullback|H4 | -11.1 | 90.6 | 15.8 | does not beat buy & hold (-11.1% vs 90.6%); outlier: falls apart out-of-sample (Sharpe -0.27 -> -0.32); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|ma_cross|D1 | 84.9 | 90.6 | 14.8 | does not beat buy & hold (84.9% vs 90.6%) |
| XAUUSD|trend_ema|D1 | 73.2 | 90.6 | 24.0 | does not beat buy & hold (73.2% vs 90.6%) |
| XAUUSD|donchian|D1 | 39.5 | 90.6 | 14.8 | does not beat buy & hold (39.5% vs 90.6%) |
| XAUUSD|macd|D1 | 52.2 | 90.6 | 17.6 | does not beat buy & hold (52.2% vs 90.6%) |
| XAUUSD|rsi_reversion|D1 | -12.9 | 90.6 | 37.6 | does not beat buy & hold (-12.9% vs 90.6%); outlier: falls apart out-of-sample (Sharpe 0.17 -> -0.58); outlier: only 44% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|D1 | 10.8 | 90.6 | 25.3 | does not beat buy & hold (10.8% vs 90.6%) |
| XAUUSD|trend_pullback|D1 | 25.2 | 90.6 | 13.0 | does not beat buy & hold (25.2% vs 90.6%); outlier: only 25% of parameter sets profitable (curve fit) |

Backtests use mid prices with half the average spread paid per side plus 0.5 bp slippage. Past results do not predict future returns. Not investment advice.
