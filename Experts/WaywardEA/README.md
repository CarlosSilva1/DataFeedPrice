# Wayward EA

Mean-reversion **scalping** Expert Advisor for MetaTrader 5, coded from the
"Mr. CapFree" walkthrough.

## Idea

Price gets *stretched* away from its mean; when it stretches too far and momentum
is exhausted, it tends to snap back. The EA measures all three:

| Component | Role |
|---|---|
| **Bollinger Bands** | Measure the stretch. Price beyond a band = overextended. The **middle line is the take-profit** (the mean it reverts to). |
| **RSI** | Confirms exhaustion. `RSI Filter = 30` derives the levels **20** (oversold) and **80** (overbought). |
| **ATR (period 1000)** | A very long, heavily-smoothed ATR. Used as a slow yardstick for the minimum candle size, the stop-loss, the trailing distance and the pending-order distance. |

Entries are **STOP orders** placed *beyond* price, so the EA never "catches a
falling knife" — it only enters once price snaps back through the pending level.

## Signals

- **Buy**: `CandleSize > ATR * CandleMult` **and** `Bid < LowerBand` **and** `RSI < 20`
  → place a **Buy Stop** at `Ask + ATR * OrderDistMult`, TP = BB middle.
- **Sell**: `CandleSize > ATR * CandleMult` **and** `Ask > UpperBand` **and** `RSI > 80`
  → place a **Sell Stop** at `Bid - ATR * OrderDistMult`, TP = BB middle.

Only one position/order at a time, and only inside the configured hour window.

## Management

- **Pending trailing** — if price keeps moving away before the stop order fills,
  the pending order is dragged along to keep a constant `ATR * OrderDistMult` gap.
- **Position trailing** — once in profit, the stop-loss follows price at
  `ATR * 0.2`.
- **Order expiry** — pending orders older than `Max pending age (bars)` are
  deleted; all pendings are cancelled when outside the trading window.

## Money management (`calcLots`)

Fixed lot, or risk a % of **Balance / Equity / Free Margin**. The lot is
`riskMoney / lossPerLot`, where `lossPerLot` is the loss for 1.0 lot over the
ATR-based stop distance, then clamped to broker `MinLot / MaxLot / LotStep`.

## Key inputs

| Input | Default | Notes |
|---|---|---|
| ATR Period | 1000 | Long/smoothed yardstick |
| SL ATR mult | 2.0 | Initial stop distance |
| Trailing ATR mult | 0.2 | Aggressive trailing |
| Order Distance ATR mult | 0.3 | Pending distance (0.2–0.3) |
| RSI Filter | 30 | → levels 20 / 80 |
| Max Spread / Slippage | 10 pts | 1 pip |
| Risk % | 1.0 | For percentage lot modes |

## Notes

- Backtest per the source used a **$1,000** deposit on **USDJPY**, "Every Tick".
- The `Higher Timeframe` input is reserved for confluence and is currently unused
  by the core logic.
- **Not investment advice.** Slippage and spread manipulation on live accounts
  can drastically change real-world results versus backtests.

## Build

Copy `WaywardEA.mq5` into `MQL5/Experts/` of your MT5 data folder and compile in
MetaEditor (F7).
