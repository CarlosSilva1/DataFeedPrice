# Portfolio report (2026-11-22T02:00:48Z)

Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.
Benchmark mode: **absolute**. MT5-style simulation: bid bars on the server clock, money account with real lots, ask/bid fills with slippage, commission, swap with triple day; portfolio combos re-verified on real ticks with the live signal delay.

## Portfolio

| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | `{"n": 2, "lo": 10, "hi": 70, "mode": "long"}` | **30.0** | 1.0x | 57.1 | 42.5 | 10.7 | 1.09 | 2.18 | 73 | 78 | 3.37 |

Per-combo numbers are the combo alone on the full deposit at its leverage.

## One account trading all combos (what the bot does)

- Deposit 10,000 -> final equity 11,391 (net 13.9%, CAGR 2.6%)
- Max drawdown 3.5%, Sharpe 0.98, profit factor 3.17, 73 trades, win rate 78%
- Max leverage used 0.3x, cash 70.0%
- Buy & hold of the same assets at the same weights: 12.4%, max DD 10.2%
- Entries skipped because the lot was below the broker minimum: {'US500|rsi_reversion|D1': '0/73'}
- Period 2021-05-24 -> 2026-05-22 (server time)

## Rejected combos

| Combo | Net % | B&H % | Max DD % | Why |
|---|---|---|---|---|
| US500|ma_cross|H4 | 39.3 | 42.5 | 15.5 | does not beat buy & hold (39.3% vs 42.5%); outlier: only 41% of parameter sets profitable (curve fit) |
| US500|trend_ema|H4 | 11.9 | 42.5 | 19.2 | does not beat buy & hold (11.9% vs 42.5%); outlier: falls apart out-of-sample (Sharpe 0.59 -> -0.45) |
| US500|donchian|H4 | 14.0 | 42.5 | 12.1 | does not beat buy & hold (14.0% vs 42.5%); outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|H4 | 14.2 | 42.5 | 14.7 | does not beat buy & hold (14.2% vs 42.5%); outlier: falls apart out-of-sample (Sharpe 0.41 -> 0.04); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|rsi_reversion|H4 | 24.0 | 42.5 | 14.2 | does not beat buy & hold (24.0% vs 42.5%); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|H4 | 34.7 | 42.5 | 12.7 | does not beat buy & hold (34.7% vs 42.5%); outlier: only 38% of parameter sets profitable (curve fit) |
| US500|trend_pullback|H4 | 18.2 | 42.5 | 11.5 | does not beat buy & hold (18.2% vs 42.5%); outlier: only 19% of parameter sets profitable (curve fit) |
| US500|ma_cross|D1 | 19.1 | 42.5 | 17.3 | does not beat buy & hold (19.1% vs 42.5%) |
| US500|trend_ema|D1 | 19.0 | 42.5 | 20.5 | does not beat buy & hold (19.0% vs 42.5%); outlier: only 25% of parameter sets profitable (curve fit) |
| US500|donchian|D1 | 16.1 | 42.5 | 10.7 | does not beat buy & hold (16.1% vs 42.5%); outlier: only 33% of parameter sets profitable (curve fit) |
| US500|macd|D1 | 4.9 | 42.5 | 16.3 | does not beat buy & hold (4.9% vs 42.5%); outlier: only 12% of parameter sets profitable (curve fit) |
| US500|bollinger_reversion|D1 | 14.0 | 42.5 | 14.8 | does not beat buy & hold (14.0% vs 42.5%); outlier: only 19 trades; outlier: falls apart out-of-sample (Sharpe 0.65 -> -0.39) |
| US500|trend_pullback|D1 | 31.9 | 42.5 | 3.4 | does not beat buy & hold (31.9% vs 42.5%) |
| XAUUSD|ma_cross|H4 | 74.4 | 102.6 | 15.5 | does not beat buy & hold (74.4% vs 102.6%); outlier: return is a statistical outlier vs all tested combos |
| XAUUSD|trend_ema|H4 | 67.4 | 102.6 | 13.8 | does not beat buy & hold (67.4% vs 102.6%) |
| XAUUSD|donchian|H4 | 41.4 | 102.6 | 18.0 | does not beat buy & hold (41.4% vs 102.6%); outlier: only 33% of parameter sets profitable (curve fit) |
| XAUUSD|macd|H4 | 35.3 | 102.6 | 24.8 | does not beat buy & hold (35.3% vs 102.6%); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|rsi_reversion|H4 | 14.3 | 102.6 | 10.6 | does not beat buy & hold (14.3% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|H4 | 9.2 | 102.6 | 14.6 | does not beat buy & hold (9.2% vs 102.6%); outlier: only 25% of parameter sets profitable (curve fit) |
| XAUUSD|trend_pullback|H4 | -12.4 | 102.6 | 12.8 | does not beat buy & hold (-12.4% vs 102.6%); outlier: falls apart out-of-sample (Sharpe -0.35 -> -0.80); outlier: only 0% of parameter sets profitable (curve fit) |
| XAUUSD|ma_cross|D1 | 67.9 | 102.6 | 17.2 | does not beat buy & hold (67.9% vs 102.6%) |
| XAUUSD|trend_ema|D1 | 78.3 | 102.6 | 19.6 | does not beat buy & hold (78.3% vs 102.6%); outlier: profit factor 5.54 > 5.0; outlier: return is a statistical outlier vs all tested combos |
| XAUUSD|donchian|D1 | 16.9 | 102.6 | 13.2 | does not beat buy & hold (16.9% vs 102.6%) |
| XAUUSD|macd|D1 | 22.9 | 102.6 | 14.5 | does not beat buy & hold (22.9% vs 102.6%) |
| XAUUSD|rsi_reversion|D1 | -11.7 | 102.6 | 39.0 | does not beat buy & hold (-11.7% vs 102.6%); outlier: falls apart out-of-sample (Sharpe 0.25 -> -0.51); outlier: only 31% of parameter sets profitable (curve fit) |
| XAUUSD|bollinger_reversion|D1 | 17.9 | 102.6 | 7.6 | does not beat buy & hold (17.9% vs 102.6%) |
| XAUUSD|trend_pullback|D1 | 8.1 | 102.6 | 12.8 | does not beat buy & hold (8.1% vs 102.6%); outlier: only 19% of parameter sets profitable (curve fit) |

Past results do not predict future returns. Not investment advice.
