# Portfolio report (2026-11-22T02:01:41Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **risk_matched**. MT5-style simulation: bid bars on the server clock, money account with real lots, ask/bid fills with slippage, commission, swap with triple day; portfolio combos re-verified on real ticks with the live signal delay.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **30.0** | 2.24x | 167.3 | 42.5 | 23.7 | 1.11 | 2.20 | 73 | 78 | 3.84 |
| XAUUSD|ma_cross|H4 | `{"fast": 10, "slow": 50, "mode": "long"}` | **30.0** | 1.6x | 137.9 | 102.6 | 26.7 | 1.03 | 1.30 | 96 | 30 | 2.25 |
| XAUUSD|trend_ema|H4 | `{"n": 50, "mode": "long"}` | **30.0** | 1.63x | 141.6 | 102.6 | 22.4 | 1.04 | 1.61 | 290 | 24 | 1.74 |

Per-combo numbers are the combo alone on the full deposit at its leverage.

## One account trading all combos (what the bot does)

- Deposit 10,000 -> final equity 22,265 (net 122.6%, CAGR 17.4%)
- Max drawdown 14.8%, Sharpe 1.41, profit factor 2.32, 459 trades, win rate 34%
- Max leverage used 1.58x, cash 10.0%
- Buy & hold of the same assets at the same weights: 73.9%, max DD 22.4%
- Entries skipped because the lot was below the broker minimum: {'US500|rsi_reversion|D1': '0/73', 'XAUUSD|ma_cross|H4': '0/96', 'XAUUSD|trend_ema|H4': '0/290'}
- Period 2021-05-24 -> 2026-05-22 (server time)

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 76.2 | 42.5 | 27.7 | outlier: only 41% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | 17.3 | 42.5 | 34.2 | does not beat buy & hold (17.3% vs 42.5%); outlier: falls apart out-of-sample (Sharpe 0.60 -> -0.49) |
| US500|donchian|H4 | 29.6 | 42.5 | 25.1 | does not beat buy & hold (29.6% vs 42.5%); outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|H4 | 21.5 | 42.5 | 24.1 | does not beat buy & hold (21.5% vs 42.5%); outlier: falls apart out-of-sample (Sharpe 0.42 -> 0.05); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|rsi_reversion|H4 | 55.3 | 42.5 | 29.4 | outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 80.4 | 42.5 | 25.7 | outlier: only 38% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 59.8 | 42.5 | 32.7 | outlier: only 19% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | 33.1 | 42.5 | 30.6 | does not beat buy & hold (33.1% vs 42.5%) |
| US500|trend_ema|D1 | 30.7 | 42.5 | 33.0 | does not beat buy & hold (30.7% vs 42.5%); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 33.6 | 42.5 | 22.6 | does not beat buy & hold (33.6% vs 42.5%); outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|D1 | 2.5 | 42.5 | 30.1 | does not beat buy & hold (2.5% vs 42.5%); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|D1 | 22.0 | 42.5 | 23.6 | does not beat buy & hold (22.0% vs 42.5%); outlier: only 19 trades; outlier: falls apart out-of-sample (Sharpe 0.65 -> -0.32) |
| US500|trend_pullback|D1 | 128.4 | 42.5 | 10.1 | outlier: profit factor 5.05 > 5.0 |
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
