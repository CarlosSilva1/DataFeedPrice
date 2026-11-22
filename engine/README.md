# Portfolio engine

Your own replacement for the "backtest → portfolio → Hot Backtests → one bot" flow, running on the
repo's real tick data with MT5-style execution.

```
ticks (US500/, XAUUSD/) ─► engine/bars.py ─► H1/H4/D1 bars (engine/data/bars, cached)
                                         └─► engine/livefeed.py appends new hours from Dukascopy
bars ─► engine/strategies.py (7 strategies × param grids)
     ─► engine/backtest.py   (MT5 model: bid/ask fills, slippage, commission, swap)
     ─► engine/portfolio.py  (rules, outlier filter, %NAV sizing) ─► engine/ticksim.py (real ticks + latency re-check)
     ─► engine/hot_backtests/ (Hot Backtests, portfolio, report)
     ─► engine/bot.py        (one bot, pair mapping + STOP, target positions) ─► engine/output/orders_latest.json
     ─► mt5/PortfolioBot.mq5 (EA that rebalances your MT5 account to those targets)
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
| Beats buy & hold, same timeframe | Full-period net return > buy & hold of the same CFD over the same bars, with the same swap and costs |
| Max drawdown < 50% | Full-period max drawdown on the equity curve |
| No "too good to be true" | < 20 trades, Sharpe > 3, profit factor > 5, win rate > 85%, return > 3.5 robust z-scores above all combos, out-of-sample Sharpe ≤ 0 or < 30% of in-sample, < 50% of the strategy's parameter sets profitable |
| Optimal %NAV | 50% mean/variance (Kelly direction) + 50% equal-risk, capped 30% per combo and 60% per asset; remainder is cash |
| Parameters | Chosen on the first 70% of data only, then checked on the last 30% |
| Final gate | Survivors are re-run on real ticks with latency and must pass again |

`--benchmark risk_matched` scales each strategy to buy & hold's volatility (0.25x–3x) before the
comparison. The leverage is stored per combo and the bot trades it.

## MT5-style execution (engine/backtest.py, engine/ticksim.py, engine/config/symbols.json)

- Signal on bar close → order on the first tick of the next bar (+ latency 150 ms ± 100 ms in the tick pass).
- Buys fill at ASK, sells at BID, plus `slippage_points` against you, plus `extra_spread_points/2`.
- Commission per lot per side; swap long/short per year charged every rollover (21:00 UTC).
- **Put your broker's real numbers in `engine/config/symbols.json`.** Swap alone moves buy & hold on gold from +140% to +91% over 2021-2026.

## One bot (engine/config/bot.json)

- `bot_id`: your bot's ID. The bot refuses to run while it is `SET_ME`.
- `available_pairs`: exact symbol names your bot/broker has. Assets are matched through `equivalents`
  (e.g. US500 → SPX500, US500.cash; XAUUSD → GOLD, XAUUSD.r). Unmapped asset → **STOP** with its name.
- `benchmark`: which portfolio the bot trades.
- Stale data (> `max_data_age_hours`) → **STOP**, nothing is sent.

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

Copy to `MQL5/Experts`, compile in MetaEditor, allow WebRequest to `https://raw.githubusercontent.com`,
set `BotId` and `OrdersURL` (raw URL of `engine/output/orders_latest.json` on the branch the scheduled
task pushes to), attach to one chart. Starts with `DryRun=true`. Not compiled or tested here: use a demo account first.

Not investment advice. Backtests do not guarantee future results.
