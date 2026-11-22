# Engine results to compare with the MT5 Strategy Tester

Deposit 10,000. Times are server time. Each combo alone on the full deposit.
Compare the **tester** rows with MT5; the **live** rows show the same combo with the bot's real delay.

| Combo | Portfolio | Symbol / TF | EA inputs | Mode | Trades | Net profit | Net % | Max DD % | Profit factor | Win % | File |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US500|rsi_reversion|D1 | absolute | US500 D1 | `Strategy=RSI_REVERSION; Exposure=1.0; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | tester | 73 | 5,740.86 | 57.4 | 10.7 | 3.37 | 75 | `US500_rsi_reversion_D1_absolute_tester.csv` |
| US500|rsi_reversion|D1 | absolute | US500 D1 | `Strategy=RSI_REVERSION; Exposure=1.0; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | live | 73 | 5,714.37 | 57.1 | 10.7 | 3.37 | 78 | `US500_rsi_reversion_D1_absolute_live.csv` |
| US500|rsi_reversion|D1 | risk_matched | US500 D1 | `Strategy=RSI_REVERSION; Exposure=2.24; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | tester | 73 | 17,030.65 | 170.3 | 23.3 | 3.88 | 75 | `US500_rsi_reversion_D1_risk_matched_tester.csv` |
| US500|rsi_reversion|D1 | risk_matched | US500 D1 | `Strategy=RSI_REVERSION; Exposure=2.24; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50` | live | 73 | 16,729.31 | 167.3 | 23.7 | 3.84 | 78 | `US500_rsi_reversion_D1_risk_matched_live.csv` |
| XAUUSD|ma_cross|H4 | risk_matched | XAUUSD H4 | `Strategy=MA_CROSS; Exposure=1.6; FastEMA=10; SlowEMA=50` | tester | 96 | 13,974.60 | 139.7 | 26.4 | 2.28 | 31 | `XAUUSD_ma_cross_H4_risk_matched_tester.csv` |
| XAUUSD|ma_cross|H4 | risk_matched | XAUUSD H4 | `Strategy=MA_CROSS; Exposure=1.6; FastEMA=10; SlowEMA=50` | live | 96 | 13,787.13 | 137.9 | 26.7 | 2.25 | 30 | `XAUUSD_ma_cross_H4_risk_matched_live.csv` |
| XAUUSD|trend_ema|H4 | risk_matched | XAUUSD H4 | `Strategy=TREND_EMA; Exposure=1.63; TrendEMA=50` | tester | 290 | 13,553.93 | 135.5 | 21.7 | 1.70 | 23 | `XAUUSD_trend_ema_H4_risk_matched_tester.csv` |
| XAUUSD|trend_ema|H4 | risk_matched | XAUUSD H4 | `Strategy=TREND_EMA; Exposure=1.63; TrendEMA=50` | live | 290 | 14,155.93 | 141.6 | 22.4 | 1.74 | 24 | `XAUUSD_trend_ema_H4_risk_matched_live.csv` |
