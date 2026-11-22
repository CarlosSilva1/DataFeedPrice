"""Export the engine's trades for the portfolio combos, to compare with an MT5
Strategy Tester report of mt5/EngineStrategy.mq5.

For every combo in engine/hot_backtests/portfolio_<benchmark>.json it runs the
combo alone on the full deposit at its leverage, twice:
  - "tester": fills on the bar's first tick, no delay  -> compare this with MT5
  - "live":   fills on real ticks after the signal delay (what the bot gets)
and writes engine/validation/<combo>_<benchmark>_<mode>.csv (times in server time)
plus engine/validation/SUMMARY.md.

Usage: python -m engine.export_trades
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import backtest, bars, strategies, ticksim

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "validation"
EA = {"rsi_reversion": "RSI_REVERSION", "ma_cross": "MA_CROSS", "trend_ema": "TREND_EMA"}


def trades_frame(df: pd.DataFrame, r: dict, fills) -> pd.DataFrame:
    fb, fs = fills
    rows = []
    for n, t in enumerate(r["trade_list"], 1):
        i, j = t["entry_i"], t["exit_i"]
        is_open = t.get("open", False)
        rows.append({
            "n": n, "type": "buy" if t["lots"] > 0 else "sell", "lots": round(abs(t["lots"]), 2),
            "entry_time": df.index[i], "entry_price": round(float(fb.iloc[i] if t["lots"] > 0 else fs.iloc[i]), 3),
            "exit_time": "" if is_open else df.index[j],
            "exit_price": "" if is_open else round(float(fs.iloc[j] if t["lots"] > 0 else fb.iloc[j]), 3),
            "profit_incl_commission_swap": round(float(t["pnl"]), 2),
        })
    return pd.DataFrame(rows)


def ea_inputs(c: dict) -> str:
    p = c["params"]
    s = f"Strategy={EA.get(c['strategy'], '(not in EA)')}; Exposure={c['leverage']}"
    if c["strategy"] == "rsi_reversion":
        s += f"; RsiPeriod={p['n']}; RsiBuyBelow={p['lo']}; RsiExitAbove=50"
    elif c["strategy"] == "ma_cross":
        s += f"; FastEMA={p['fast']}; SlowEMA={p['slow']}"
    elif c["strategy"] == "trend_ema":
        s += f"; TrendEMA={p['n']}"
    return s


def main() -> None:
    OUT.mkdir(exist_ok=True)
    L = ["# Engine results to compare with the MT5 Strategy Tester", "",
         f"Deposit {backtest.deposit():,.0f}. Times are server time. Each combo alone on the full deposit.",
         "Compare the **tester** rows with MT5; the **live** rows show the same combo with the bot's real delay.", "",
         "| Combo | Portfolio | Symbol / TF | EA inputs | Mode | Trades | Net profit | Net % | Max DD % | Profit factor | Win % | File |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for bench in ["absolute", "risk_matched"]:
        p = ROOT / "hot_backtests" / f"portfolio_{bench}.json"
        if not p.exists():
            continue
        for c in json.loads(p.read_text())["combos"]:
            df = bars.load_bars(c["asset"], c["timeframe"])
            sig = strategies.signal(c["strategy"], df, c["params"])
            runs = {"tester": (backtest.run(df, sig, c["timeframe"], c["asset"], c["leverage"]),
                               backtest.bar_fills(df, backtest.spec(c["asset"])))}
            live = ticksim.run(df, sig, c["timeframe"], c["asset"], c["leverage"])
            runs["live"] = (live, live["_fills"])
            for mode, (r, fills) in runs.items():
                name = f"{c['id'].replace('|', '_')}_{bench}_{mode}.csv"
                trades_frame(df, r, fills).to_csv(OUT / name, index=False)
                L.append(f"| {c['id']} | {bench} | {c['asset']} {c['timeframe']} | `{ea_inputs(c)}` | {mode} | {r['trades']} | "
                         f"{r['final_equity'] - r['deposit']:,.2f} | {r['net_return_pct']:.1f} | {r['max_drawdown_pct']:.1f} | "
                         f"{r['profit_factor']:.2f} | {r['win_rate_pct']:.0f} | `{name}` |")
            print(f"{c['id']} ({bench}): tester {runs['tester'][0]['net_return_pct']:.1f}%  live {live['net_return_pct']:.1f}%")
    (OUT / "SUMMARY.md").write_text("\n".join(L) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT.parent)}/")


if __name__ == "__main__":
    main()
