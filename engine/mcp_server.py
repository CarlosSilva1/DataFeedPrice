"""MCP server for the engine: lets any MCP-capable AI client (Claude Code,
Claude Desktop, Cursor, ChatGPT desktop, VS Code, ...) run backtests, build the
portfolio, read Hot Backtests and produce the bot's orders.

Run (stdio):  python -m engine.mcp_server
Works with the official `mcp` Python SDK 1.x (FastMCP) and 2.x (MCPServer).
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import backtest, bars, bot, livefeed, portfolio, strategies, ticksim

ROOT = Path(__file__).resolve().parent
HOT = ROOT / "hot_backtests"

mcp = _Server(
    "datafeedprice-engine",
    instructions=(
        "Backtesting + portfolio engine on real tick data with MT5-style execution "
        "(bid/ask fills, latency, slippage, commission, swap). Typical flow: list_assets -> "
        "build_portfolio -> get_hot_backtests -> bot_orders. bot_orders refuses to trade when an "
        "asset has no equivalent pair on the bot or when data is stale; relay that STOP to the user."
    ),
)


def _strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if k not in ("returns", "equity", "bh_equity", "position")}


@mcp.tool()
def list_assets() -> dict:
    """Assets with cached bars, their data range, strategies and their parameter grids."""
    out = {}
    for s in bars.available_symbols():
        h1 = bars.load_bars(s, "H1")
        out[s] = {"first_bar": str(h1.index[0]), "last_bar": str(h1.index[-1]), "h1_bars": len(h1)}
    return {"assets": out, "timeframes": list(bars.TF_RULES), "strategies": strategies.GRID}


@mcp.tool()
def run_backtest(asset: str, strategy: str, timeframe: str, params: dict, real_ticks: bool = False) -> dict:
    """Backtest one asset+strategy+timeframe with given params. real_ticks=True fills every
    order on real ticks with latency (slower, closest to live)."""
    df = bars.load_bars(asset, timeframe)
    sig = strategies.signal(strategy, df, params)
    r = ticksim.run(df, sig, timeframe, asset) if real_ticks else backtest.run(df, sig, timeframe, asset)
    return _strip(r)


@mcp.tool()
def build_portfolio(benchmark: str = "absolute") -> dict:
    """Run the full Portfolio Prompt: backtest every combo, keep those that beat buy & hold
    with max DD < 50% and no too-good-to-be-true flags, size them by risk/reward (%NAV),
    re-verify on real ticks, and save them to Hot Backtests. benchmark: absolute | risk_matched."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        portfolio.main(None, benchmark)
    return json.loads((HOT / f"portfolio_{benchmark}.json").read_text())


@mcp.tool()
def get_portfolio(benchmark: str = "absolute") -> dict:
    """The last saved portfolio for a benchmark mode (no recomputation)."""
    return json.loads((HOT / f"portfolio_{benchmark}.json").read_text())


@mcp.tool()
def get_report(benchmark: str = "absolute") -> str:
    """Markdown report: chosen combos with %NAV and KPIs, and why every other combo was rejected."""
    return (HOT / f"PORTFOLIO_REPORT_{benchmark}.md").read_text()


@mcp.tool()
def get_hot_backtests() -> dict:
    """All combos ever saved to Hot Backtests, per benchmark mode, with in_current_portfolio flags."""
    p = HOT / "hot_backtests.json"
    return json.loads(p.read_text()) if p.exists() else {}


@mcp.tool()
def update_prices(max_hours: int = 4800) -> str:
    """Download new hourly bars from Dukascopy for every asset (needs network access to
    datafeed.dukascopy.com)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        for s in bars.available_symbols():
            livefeed.update(s, max_hours)
    return buf.getvalue()


@mcp.tool()
def check_bot_pairs() -> dict:
    """Map each portfolio asset to the bot's equivalent pair. Returns a STOP message if any is missing."""
    cfg = bot.config()
    try:
        return {"ok": True, "bot_id": cfg["bot_id"],
                "mapping": bot.resolve_pairs(sorted({c["asset"] for c in bot.portfolio(cfg)["combos"]}), cfg)}
    except bot.BotStop as e:
        return {"ok": False, "stop": str(e)}


@mcp.tool()
def bot_orders(send: bool = False) -> dict:
    """Target positions for the single bot (one per pair, % of NAV, netted across combos).
    send=True POSTs them to the bot webhook. Returns a STOP message instead when trading is unsafe."""
    buf, err = io.StringIO(), io.StringIO()
    from contextlib import redirect_stderr
    with redirect_stdout(buf), redirect_stderr(err):
        code = bot.main(["--send"] if send else [])
    orders = json.loads((ROOT / "output" / "orders_latest.json").read_text()) if (ROOT / "output" / "orders_latest.json").exists() else None
    return {"ok": code == 0, "stop": err.getvalue().strip() or None, "orders": orders}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
