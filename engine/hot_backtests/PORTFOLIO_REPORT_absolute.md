# Portfolio report (2026-11-22T03:17:06Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **absolute**. MT5-style simulation: bid bars on the server clock, money account with real lots, ask/bid fills with slippage, commission, swap with triple day; portfolio combos re-verified on real ticks with the live signal delay.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **30.0** | 1.0x | 51.2 | 12.0 | 12.1 | 0.99 | 2.12 | 73 | 75 | 2.96 |
| US500|trend_pullback|D1 | `{"trend": 100, "n": 2, "lo": 10, "mode": "long"}` | **30.0** | 1.0x | 27.7 | 12.0 | 3.8 | 1.07 | 1.61 | 44 | 77 | 3.80 |

Per-combo numbers are the combo alone on the full deposit at its leverage.

## One account trading all combos (what the bot does)

- Deposit 10,000 -> final equity 12,204 (net 22.0%, CAGR 4.1%)
- Max drawdown 4.8%, Sharpe 1.09, profit factor 3.11, 117 trades, win rate 76%
- Max leverage used 0.6x, cash 40.0%
- Buy & hold of the same assets at the same weights: 7.2%, max DD 25.7%
- Entries skipped because the lot was below the broker minimum: {'US500|rsi_reversion|D1': '0/73', 'US500|trend_pullback|D1': '0/44'}
- Period 2021-05-24 -> 2026-05-25 (server time)

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 17.8 | 12.1 | 17.9 | outlier: only 5% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | -4.9 | 12.1 | 21.8 | does not beat buy & hold (-4.9% vs 12.1%); outlier: falls apart out-of-sample (Sharpe 0.21 -> -0.58); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|donchian|H4 | 0.0 | 12.1 | 16.1 | does not beat buy & hold (0.0% vs 12.1%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|macd|H4 | 0.8 | 12.1 | 18.1 | does not beat buy & hold (0.8% vs 12.1%); outlier: falls apart out-of-sample (Sharpe 0.12 -> -0.02); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|rsi_reversion|H4 | 19.2 | 12.1 | 16.9 | outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 26.5 | 12.1 | 13.3 | outlier: only 38% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 7.2 | 12.1 | 9.7 | does not beat buy & hold (7.2% vs 12.1%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | -3.3 | 12.0 | 28.4 | does not beat buy & hold (-3.3% vs 12.0%); outlier: only 9% of parameter sets profitable (curve fit) |
| US500|trend_ema|D1 | -1.8 | 12.0 | 25.6 | does not beat buy & hold (-1.8% vs 12.0%); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 2.4 | 12.0 | 16.0 | does not beat buy & hold (2.4% vs 12.0%); outlier: only 17% of parameter sets profitable (curve fit) |
| US500|macd|D1 | -10.3 | 12.0 | 20.8 | does not beat buy & hold (-10.3% vs 12.0%); outlier: falls apart out-of-sample (Sharpe -0.20 -> -0.05); outlier: only 0% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|D1 | 7.7 | 12.0 | 15.6 | does not beat buy & hold (7.7% vs 12.0%); outlier: only 19 trades; outlier: falls apart out-of-sample (Sharpe 0.52 -> -0.43) |
| XAUUSD|ma_cross|H4 | 74.4 | 102.6 | 15.5 | does not beat buy & hold (74.4% vs 102.6%) |
| XAUUSD|trend_ema|H4 | 67.4 | 102.6 | 13.8 | does not beat buy & hold (67.4% vs 102.6%) |
| XAUUSD|donchian|H4 | 41.4 | 102.6 | 18.0 | does not beat buy & hold (41.4% vs 102.6%); outlier: only 33% of parameter sets profitable (curve fit) |
| XAUUSD|macd|H4 | 35.3 | 102.6 | 24.8 | does not beat buy & hold (35.3% vs 102.6%); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|rsi_reversion|H4 | 14.3 | 102.6 | 10.6 | does not beat buy & hold (14.3% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|H4 | 9.2 | 102.6 | 14.6 | does not beat buy & hold (9.2% vs 102.6%); outlier: only 25% of parameter sets profitable (curve fit) |
| XAUUSD|trend_pullback|H4 | -12.4 | 102.6 | 12.8 | does not beat buy & hold (-12.4% vs 102.6%); outlier: falls apart out-of-sample (Sharpe -0.35 -> -0.80); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|ma_cross|D1 | 67.9 | 102.6 | 17.2 | does not beat buy & hold (67.9% vs 102.6%) |
| XAUUSD|trend_ema|D1 | 78.3 | 102.6 | 19.6 | does not beat buy & hold (78.3% vs 102.6%); outlier: profit factor 5.54 > 5.0 |
| XAUUSD|donchian|D1 | 16.9 | 102.6 | 13.2 | does not beat buy & hold (16.9% vs 102.6%) |
| XAUUSD|macd|D1 | 22.9 | 102.6 | 14.5 | does not beat buy & hold (22.9% vs 102.6%) |
| XAUUSD|rsi_reversion|D1 | -11.7 | 102.6 | 39.0 | does not beat buy & hold (-11.7% vs 102.6%); outlier: falls apart out-of-sample (Sharpe 0.25 -> -0.51); outlier: only 31% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|D1 | 17.9 | 102.6 | 7.6 | does not beat buy & hold (17.9% vs 102.6%) |
| XAUUSD|trend_pullback|D1 | 8.1 | 102.6 | 12.8 | does not beat buy & hold (8.1% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |

Past results do not predict future returns. Not investment advice.
