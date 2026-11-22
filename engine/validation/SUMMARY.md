# Engine results to compare with the MT5 Strategy Tester

Deposit 10,000. Times are server time. Each combo alone on the full deposit.
Compare the **tester** rows with MT5; the **live** rows show the same combo with the bot's real delay.

| Combo | Portfolio | Symbol / TF | EA inputs | Mode | Trades | Net profit | Net % | Max DD % | Profit factor | Win % | File |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | absolute | US500 D1 | `Strategy=RSI_REVERSION; Exposure=1.0; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | tester | 73 | 5,160.56 | 51.6 | 12.0 | 2.96 | 75 | `US500_rsi_reversion_D1_absolute_tester.csv` |
| US500|rsi_reversion|D1 | absolute | US500 D1 | `Strategy=RSI_REVERSION; Exposure=1.0; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | live | 73 | 5,117.12 | 51.2 | 12.1 | 2.96 | 75 | `US500_rsi_reversion_D1_absolute_live.csv` |
| US500|trend_pullback|D1 | absolute | US500 D1 | `Strategy=(not in EA); Exposure=1.0` | tester | 44 | 2,959.72 | 29.6 | 3.6 | 4.27 | 77 | `US500_trend_pullback_D1_absolute_tester.csv` |
| US500|trend_pullback|D1 | absolute | US500 D1 | `Strategy=(not in EA); Exposure=1.0` | live | 44 | 2,765.84 | 27.7 | 3.8 | 3.80 | 77 | `US500_trend_pullback_D1_absolute_live.csv` |
| US500|rsi_reversion|D1 | risk_matched | US500 D1 | `Strategy=RSI_REVERSION; Exposure=2.71; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | tester | 73 | 18,841.16 | 188.4 | 31.3 | 3.44 | 75 | `US500_rsi_reversion_D1_risk_matched_tester.csv` |
| US500|rsi_reversion|D1 | risk_matched | US500 D1 | `Strategy=RSI_REVERSION; Exposure=2.71; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | live | 73 | 18,496.32 | 185.0 | 31.6 | 3.44 | 75 | `US500_rsi_reversion_D1_risk_matched_live.csv` |
| US500|trend_pullback|D1 | risk_matched | US500 D1 | `Strategy=(not in EA); Exposure=3.0` | tester | 44 | 11,379.19 | 113.8 | 10.6 | 4.43 | 77 | `US500_trend_pullback_D1_risk_matched_tester.csv` |
| US500|trend_pullback|D1 | risk_matched | US500 D1 | `Strategy=(not in EA); Exposure=3.0` | live | 44 | 10,430.66 | 104.3 | 11.1 | 3.98 | 77 | `US500_trend_pullback_D1_risk_matched_live.csv` |
| XAUUSD|ma_cross|H4 | risk_matched | XAUUSD H4 | `Strategy=MA_CROSS; Exposure=1.6; FastEMA=10; SlowEMA=50` | tester | 96 | 13,974.60 | 139.7 | 26.4 | 2.28 | 31 | `XAUUSD_ma_cross_H4_risk_matched_tester.csv` |
| XAUUSD|ma_cross|H4 | risk_matched | XAUUSD H4 | `Strategy=MA_CROSS; Exposure=1.6; FastEMA=10; SlowEMA=50` | live | 96 | 13,787.13 | 137.9 | 26.7 | 2.25 | 30 | `XAUUSD_ma_cross_H4_risk_matched_live.csv` |
| XAUUSD|trend_ema|H4 | risk_matched | XAUUSD H4 | `Strategy=TREND_EMA; Exposure=1.63; TrendEMA=50` | tester | 290 | 13,553.93 | 135.5 | 21.7 | 1.70 | 23 | `XAUUSD_trend_ema_H4_risk_matched_tester.csv` |
| XAUUSD|trend_ema|H4 | risk_matched | XAUUSD H4 | `Strategy=TREND_EMA; Exposure=1.63; TrendEMA=50` | live | 290 | 14,155.93 | 141.6 | 22.4 | 1.74 | 24 | `XAUUSD_trend_ema_H4_risk_matched_live.csv` |
