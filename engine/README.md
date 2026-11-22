# Portfolio engine

Your own replacement for the "backtest → portfolio → Hot Backtests → one bot" flow, running on the
repo's real tick data with MT5-style execution.

```
ticks (US500/, XAUUSD/) ─► engine/bars.py ─► H1/H4/D1 bars (engine/data/bars, cached)
                                         └─► engine/livefeed.py appends new hours from Dukascopy
bars ─► engine/strategies.py (7 strategies × param grids)
     ─► engine/backtest.py   (MT5-style money account: lots, ask/bid fills, slippage, commission, swap)
     ─► engine/portfolio.py  (rules, outlier filter, %NAV sizing, shared-account simulation) ─► engine/ticksim.py (real ticks + delay re-check)
     ─► engine/hot_backtests/ (Hot Backtests, portfolio, report)
     ─► engine/bot.py        (one bot, pair mapping + STOP, per-combo orders) ─► engine/output/orders_latest.json
     ─► mt5/PortfolioBot.mq5 (EA that holds one position per combo on your MT5 account)
engine/mcp_server.py exposes all of it as MCP tools to any AI client.
```

## Quick start

```bash
pip install -r engine/requirements.txt
python -m engine.bars                                  # only needed after new tick files are added
python -m engine.livefeed                              # bring bars up to date (needs datafeed.dukascopy.com)
python -m engine.portfolio --benchmark absolute        # or risk_matched
python -m engine.bot --check                           # map assets to the bot's pairs (STOP if missing)
python -m engine.bot                                   # write orders_latest.json (add --send for webhook)
```

## The Portfolio Prompt as rules (engine/portfolio.py)

| Rule | Implementation |
|---|---|
| Beats buy & hold, same timeframe | Full-period net return > buy & hold of the same CFD (bought on the first bar with real lots, same fills, commission and swap) |
| Max drawdown < 50% | Full-period max drawdown of account equity |
| No "too good to be true" | < 20 trades, Sharpe > 3, profit factor > 5, win rate > 85%, return > 3.5 robust z-scores above all combos, out-of-sample Sharpe <= 0 or < 30% of in-sample, < 50% of the strategy's parameter sets profitable |
| Optimal %NAV | 50% mean/variance (Kelly direction) + 50% equal-risk, capped 30% per combo and 60% per asset; remainder is cash |
| Parameters | Chosen on the first 70% of data only, then checked on the last 30% |
| Real-tick gate | Survivors are re-run on real ticks with the live signal delay and must pass again |
| Tradable | One shared account is simulated with real lots; combos whose lot falls below the broker minimum for the deposit are dropped |

`--benchmark risk_matched` scales each strategy to buy & hold's volatility (0.25x-3x) before the
comparison. The leverage is stored per combo and the bot trades it.

## How it mirrors the MT5 Strategy Tester

| MT5 | Engine |
|---|---|
| Bars from Bid prices | `engine/bars.py` builds bid OHLC from the ticks |
| Bars on the broker server clock | D1/H4 cut on `server_time` in `engine/config/symbols.json` (default New York close = 00:00: 5 daily bars a week, no Sunday bar) |
| EA acts on a new bar | Signal on the closed bar, order when the next bar opens |
| Buy at Ask, sell at Bid | Real first-tick bid/ask of the bar (+ `slippage_points`, + `extra_spread_points/2`) |
| "Every tick based on real ticks" + delay | `engine/ticksim.py`: fill at the real tick `signal_delay_minutes` (20 +/- 10, the scheduled task + EA pipeline) + `latency_ms` after the bar opens |
| Deposit, lots, volume min/step | Money account (`account.initial_deposit`), lots = exposure x equity / (price x contract), rounded down, fixed at entry |
| Commission per lot | `commission_per_lot_per_side_usd` |
| Swap, triple-swap day | % per year / 360 of notional at each server-midnight rollover, x3 on `swap_triple_weekday`, none on weekend rollovers |
| Bollinger Bands / RSI / EMA | Population std for Bands, Wilder smoothing for RSI, standard EMA |
| Profit factor, win rate, trades | From money P&L of closed trades |

**Put your broker's real numbers in `engine/config/symbols.json`** (contract size, volume min/step,
commission, swaps, triple day, server time). They decide the result: swap alone takes tens of
percentage points off 5 years of buy & hold.

Not modelled (state this when comparing with an MT5 report): margin call / stop-out; shorts are
marked at bid (spread charged at exit instead of entry); broker-specific ticks and spreads (the data
is Dukascopy's); requotes and partial fills; holidays with shifted swap days; in the tick pass the
jitter is random, so two runs of MT5 with "random delay" would not match each other either.
To validate against MT5 itself: run the same strategy in the Strategy Tester ("Every tick based on
real ticks") on the same symbol and period and compare trades count, net profit and max drawdown.

## One bot (engine/config/bot.json, engine/bot.py)

- `bot_id`: your bot's ID. The bot refuses to run while it is `SET_ME`.
- `available_pairs`: exact symbol names your bot/broker has. Assets are matched through `equivalents`
  (e.g. US500 -> SPX500, US500.cash; XAUUSD -> GOLD, XAUUSD.r). Unmapped asset -> **STOP** with its name.
- `benchmark`: which portfolio the bot trades.
- Signals come only from CLOSED bars (server clock), as in the backtest.
- Orders are per combo: pair, `exposure_pct_nav` (= %NAV x leverage x signal) and a `magic_offset`.
- Stale data (> `max_data_age_hours`) -> **STOP**, nothing is sent.

## MCP server (any AI)

`python -m engine.mcp_server` (stdio). Tools: `list_assets`, `run_backtest`, `build_portfolio`,
`get_portfolio`, `get_report`, `get_hot_backtests`, `update_prices`, `check_bot_pairs`, `bot_orders`.

- Claude Code: `.mcp.json` at the repo root registers it automatically.
- Claude Desktop / Cursor / others: add to their MCP config:

```json
{ "mcpServers": { "datafeedprice-engine": {
    "command": "python3", "args": ["-m", "engine.mcp_server"], "cwd": "/path/to/DataFeedPrice" } } }
```

## MT5 EA (mt5/PortfolioBot.mq5)

Holds one position per combo (magic = `Magic` + `magic_offset`), sized when it opens exactly like the
account simulation, closes it when the signal goes flat or flips, retries while the market is closed.
Needs a hedging account. Copy to `MQL5/Experts`, compile in MetaEditor, allow WebRequest to
`https://raw.githubusercontent.com`, set `BotId` and `OrdersURL` (raw URL of
`engine/output/orders_latest.json` on the branch the scheduled task pushes to), attach to one chart.
Starts with `DryRun=true`. Not compiled or tested here: use a demo account first.

Not investment advice. Backtests do not guarantee future results.
