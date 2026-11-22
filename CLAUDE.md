# DataFeedPrice

Tick data (US500/, XAUUSD/ parquet, Dukascopy source) plus a backtest/portfolio/bot engine in `engine/`.
Read `engine/README.md` before changing the engine.

- Setup: `pip install -r engine/requirements.txt`
- Portfolio: `python -m engine.portfolio --benchmark absolute|risk_matched` → `engine/hot_backtests/`
- Bot orders: `python -m engine.bot [--check|--send]` → `engine/output/orders_latest.json`; exit code 2 = STOP, report the message to the user verbatim and do not trade.
- New prices: `python -m engine.livefeed` (needs datafeed.dukascopy.com on the network allowlist).
- MCP server: `.mcp.json` registers `engine/mcp_server.py` for Claude Code.
- Scheduled bot run instructions: `engine/SCHEDULED_TASK_PROMPT.md`.
- Never trade when the bot STOPs (missing pair, unset bot_id, stale data, empty portfolio).
