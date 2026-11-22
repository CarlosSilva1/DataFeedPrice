"""Portfolio builder: the "Portfolio Prompt" as code.

1. Backtest every asset x strategy x timeframe x parameter set.
2. Per combo (asset + strategy + timeframe) choose parameters on the first 70%
   of the data (in-sample) and check them on the last 30% (out-of-sample).
3. Keep combos that, over the full period:
     - beat buy & hold on the same asset and timeframe,
     - have max drawdown < 50%,
     - are not "too good to be true" (see OUTLIER RULES).
4. Size each survivor by risk/reward (mean/variance, shrunk), with caps.
5. Save the chosen combos to engine/hot_backtests/ and write a report.

Usage:
    python -m engine.portfolio                 # all cached assets
    python -m engine.portfolio --symbols US500
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, bars, strategies, ticksim

REPO = Path(__file__).resolve().parent.parent
HOT_DIR = REPO / "engine" / "hot_backtests"

TIMEFRAMES = ["H4", "D1"]
IS_FRACTION = 0.7

# Selection rules
MAX_DD_PCT = 50.0
# OUTLIER RULES ("too good to be true")
MIN_TRADES = 20            # fewer trades = result is mostly luck
MAX_SHARPE = 3.0           # sustained Sharpe > 3 on bars is almost always a bug or curve fit
MAX_PROFIT_FACTOR = 5.0
MAX_WIN_RATE = 85.0
MIN_OOS_SHARPE_RATIO = 0.3  # out-of-sample Sharpe must keep >= 30% of in-sample Sharpe
MIN_PARAM_ROBUSTNESS = 0.5  # >= 50% of the strategy's parameter sets must be profitable in-sample
ROBUST_Z_MAX = 3.5          # net return more than 3.5 MADs above the median of all tested combos

# Allocation
MAX_PER_COMBO = 0.30
MAX_PER_ASSET = 0.60
SHRINK = 0.5               # blend of risk/reward weights with equal risk weights

# Benchmark mode
#   absolute     : strategy at 1x must beat buy & hold's return (the rule as written)
#   risk_matched : strategy is levered/delevered to buy & hold's volatility
#                  (max MAX_LEVERAGE) and must then beat buy & hold's return
BENCHMARK = "absolute"
MAX_LEVERAGE = 3.0


def _slice(df, frac, part):
    k = int(len(df) * frac)
    return df.iloc[:k] if part == "is" else df.iloc[k:]


def research(symbols: list[str]) -> list[dict]:
    combos = []
    for sym in symbols:
        for tf in TIMEFRAMES:
            df = bars.load_bars(sym, tf)
            is_df, oos_df = _slice(df, IS_FRACTION, "is"), _slice(df, IS_FRACTION, "oos")
            for name, grid in strategies.GRID.items():
                tried = []
                for p in grid:
                    pos_full = strategies.signal(name, df, p)
                    r_is = backtest.run(is_df, pos_full.loc[is_df.index], tf, sym)
                    tried.append((p, r_is, pos_full))
                eligible = [t for t in tried if t[1]["trades"] >= MIN_TRADES * IS_FRACTION] or tried
                p, r_is, pos_full = max(eligible, key=lambda t: t[1]["sharpe"])
                full = backtest.run(df, pos_full, tf, sym)
                oos = backtest.run(oos_df, pos_full.loc[oos_df.index], tf, sym)
                robustness = np.mean([t[1]["net_return_pct"] > 0 for t in tried])
                strip = lambda r: {k: v for k, v in r.items() if k not in ("returns", "equity", "bh_equity", "position")}
                combos.append({
                    "id": f"{sym}|{name}|{tf}",
                    "asset": sym, "strategy": name, "timeframe": tf, "params": p,
                    "full": strip(full), "in_sample": strip(r_is), "out_of_sample": strip(oos),
                    "param_robustness": float(robustness),
                    "leverage": 1.0,
                    "_df": df, "_pos": pos_full,
                    "_daily": (1 + full["returns"]).resample("1D").prod().sub(1),
                })
                print(f"  {sym:7s} {tf} {name:20s} net {full['net_return_pct']:8.1f}%  "
                      f"B&H {full['bh_return_pct']:7.1f}%  DD {full['max_drawdown_pct']:5.1f}%  "
                      f"Sh {full['sharpe']:5.2f}  OOS Sh {oos['sharpe']:5.2f}")
    return combos


def tick_verify(c: dict) -> None:
    """Re-run a combo on real ticks with latency and replace its KPIs."""
    df, pos, tf, sym = c["_df"], c["_pos"], c["timeframe"], c["asset"]
    k = c.get("leverage", 1.0)
    full = ticksim.run(df, pos * k, tf, sym)
    oos_df = _slice(df, IS_FRACTION, "oos")
    oos = ticksim.run(oos_df, pos.loc[oos_df.index] * k, tf, sym)
    strip = lambda r: {x: v for x, v in r.items() if x not in ("returns", "equity", "bh_equity", "position")}
    c["bar_engine_full"] = c["full"]
    c["full"], c["out_of_sample"] = strip(full), strip(oos)
    c["_daily"] = (1 + full["returns"]).resample("1D").prod().sub(1)
    c["engine"] = "real ticks + latency"


def risk_match(c: dict) -> None:
    """Scale the combo to buy & hold's volatility, then re-run it."""
    f = c["full"]
    bh_vol = c["_df"].close.pct_change().std() * np.sqrt(backtest.BARS_PER_YEAR[c["timeframe"]]) * 100
    k = float(np.clip(bh_vol / f["ann_vol_pct"], 0.25, MAX_LEVERAGE)) if f["ann_vol_pct"] > 0 else 1.0
    c["leverage"] = round(k, 2)
    df, pos, tf, sym = c["_df"], c["_pos"], c["timeframe"], c["asset"]
    oos_df = _slice(df, IS_FRACTION, "oos")
    strip = lambda r: {x: v for x, v in r.items() if x not in ("returns", "equity", "bh_equity", "position")}
    full = backtest.run(df, pos * k, tf, sym)
    c["full_1x"] = c["full"]
    c["full"] = strip(full)
    c["out_of_sample"] = strip(backtest.run(oos_df, pos.loc[oos_df.index] * k, tf, sym))
    c["_daily"] = (1 + full["returns"]).resample("1D").prod().sub(1)


def apply_rules(combos: list[dict]) -> None:
    nets = np.array([c["full"]["net_return_pct"] / max(c.get("leverage", 1.0), 1e-9) for c in combos])
    med = np.median(nets)
    mad = np.median(np.abs(nets - med)) or 1.0
    for c in combos:
        f, i, o = c["full"], c["in_sample"], c["out_of_sample"]
        why = []
        if f["net_return_pct"] <= f["bh_return_pct"]:
            why.append(f"does not beat buy & hold ({f['net_return_pct']:.1f}% vs {f['bh_return_pct']:.1f}%)")
        if f["max_drawdown_pct"] >= MAX_DD_PCT:
            why.append(f"max drawdown {f['max_drawdown_pct']:.1f}% >= {MAX_DD_PCT}%")
        out = []
        if f["trades"] < MIN_TRADES:
            out.append(f"only {f['trades']} trades")
        if f["sharpe"] > MAX_SHARPE:
            out.append(f"Sharpe {f['sharpe']:.2f} > {MAX_SHARPE}")
        if f["profit_factor"] > MAX_PROFIT_FACTOR:
            out.append(f"profit factor {f['profit_factor']:.2f} > {MAX_PROFIT_FACTOR}")
        if f["win_rate_pct"] > MAX_WIN_RATE:
            out.append(f"win rate {f['win_rate_pct']:.0f}% > {MAX_WIN_RATE}%")
        if (f["net_return_pct"] / c.get("leverage", 1.0) - med) / (1.4826 * mad) > ROBUST_Z_MAX:
            out.append("return is a statistical outlier vs all tested combos")
        if o["sharpe"] <= 0 or (i["sharpe"] > 0 and o["sharpe"] < MIN_OOS_SHARPE_RATIO * i["sharpe"]):
            out.append(f"falls apart out-of-sample (Sharpe {i['sharpe']:.2f} -> {o['sharpe']:.2f})")
        if c["param_robustness"] < MIN_PARAM_ROBUSTNESS:
            out.append(f"only {c['param_robustness']:.0%} of parameter sets profitable (curve fit)")
        c["rejected_rules"] = why
        c["outlier_flags"] = out
        c["selected"] = not why and not out


def allocate(sel: list[dict]) -> None:
    """w ~ mean/variance of daily returns (Kelly direction), shrunk toward equal
    risk, then capped per combo and per asset. Uncapped remainder stays cash."""
    if not sel:
        return
    mu = np.array([c["_daily"].mean() for c in sel])
    var = np.array([c["_daily"].var() for c in sel])
    vol = np.sqrt(var)
    kelly = np.clip(mu / var, 0, None)
    kelly = kelly / kelly.sum() if kelly.sum() > 0 else np.ones(len(sel)) / len(sel)
    eqrisk = (1 / vol) / (1 / vol).sum()
    w = SHRINK * kelly + (1 - SHRINK) * eqrisk
    assets = np.array([c["asset"] for c in sel])
    for _ in range(50):  # iterative capping with redistribution
        w = np.minimum(w, MAX_PER_COMBO)
        for a in set(assets):
            m = assets == a
            if w[m].sum() > MAX_PER_ASSET:
                w[m] *= MAX_PER_ASSET / w[m].sum()
        free = 1 - w.sum()
        room = np.array([
            min(MAX_PER_COMBO - w[k], MAX_PER_ASSET - w[assets == assets[k]].sum()) for k in range(len(w))
        ]).clip(0)
        if free < 1e-6 or room.sum() < 1e-6:
            break
        w += free * room / room.sum() * (room > 0)
    for c, x in zip(sel, w):
        c["nav_pct"] = round(float(x) * 100, 2)


def portfolio_curve(sel: list[dict]) -> tuple[dict, pd.Series, pd.Series]:
    daily = pd.concat({c["id"]: c["_daily"] for c in sel}, axis=1).fillna(0)
    w = pd.Series({c["id"]: c["nav_pct"] / 100 for c in sel})
    port = daily.mul(w, axis=1).sum(axis=1)
    eq = (1 + port).cumprod()
    # Benchmark: buy & hold of the same assets with the same per-asset weights.
    bh = []
    for a in sorted({c["asset"] for c in sel}):
        wa = sum(c["nav_pct"] for c in sel if c["asset"] == a) / 100
        r = bars.load_bars(a, "D1").close.pct_change().reindex(port.index).fillna(0)
        bh.append(r * wa)
    bh_eq = (1 + sum(bh)).cumprod()
    k = backtest.kpis(port, eq, bh_eq, pd.Series(1, index=port.index), "D1")
    for drop in ("trades", "win_rate_pct", "profit_factor", "exposure_pct"):
        k.pop(drop)
    k["cash_pct"] = round(100 - sum(c["nav_pct"] for c in sel), 2)
    return k, eq, bh_eq


def save(combos, sel, pk, eq, bh_eq) -> Path:
    HOT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    clean = lambda c: {k: v for k, v in c.items() if not k.startswith("_")}
    portfolio = {"generated_at": now, "benchmark": BENCHMARK, "portfolio_kpis": pk, "combos": [clean(c) for c in sel]}
    (HOT_DIR / f"portfolio_{BENCHMARK}.json").write_text(json.dumps(portfolio, indent=2))
    (HOT_DIR / f"all_combos_{BENCHMARK}.json").write_text(json.dumps([clean(c) for c in combos], indent=2))

    # Hot Backtests: a running list; a combo stays in it with its latest result.
    hot_path = HOT_DIR / "hot_backtests.json"
    allhot = json.loads(hot_path.read_text()) if hot_path.exists() else {}
    hot = allhot.setdefault(BENCHMARK, {})
    for c in sel:
        hot[c["id"]] = {**clean(c), "saved_at": now, "in_current_portfolio": True}
    for k in hot:
        if k not in {c["id"] for c in sel}:
            hot[k]["in_current_portfolio"] = False
    hot = allhot
    hot_path.write_text(json.dumps(hot, indent=2))

    pd.DataFrame({"portfolio": eq, "buy_hold_same_weights": bh_eq}).to_csv(HOT_DIR / f"portfolio_equity_{BENCHMARK}.csv")
    report = HOT_DIR / f"PORTFOLIO_REPORT_{BENCHMARK}.md"
    report.write_text(_report(now, combos, sel, pk))
    return report


def _report(now, combos, sel, pk) -> str:
    L = [f"# Portfolio report ({now})", "",
         "Rules: beats buy & hold over the same period, max drawdown < 50%, no too-good-to-be-true outliers.",
         f"Benchmark mode: **{BENCHMARK}**. Execution: MT5-style (first tick of next bar, bid/ask, slippage, "
         "commission, swap); portfolio combos re-verified on real ticks with latency.", "",
         "## Portfolio", "",
         "| Combo | Params | %NAV | Leverage | Net % | B&H % | Max DD % | Sharpe | OOS Sharpe | Trades | Win % | PF |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(sel, key=lambda c: -c["nav_pct"]):
        f = c["full"]
        L.append(f"| {c['id']} | `{json.dumps(c['params'])}` | **{c['nav_pct']}** | {c['leverage']}x | {f['net_return_pct']:.1f} | "
                 f"{f['bh_return_pct']:.1f} | {f['max_drawdown_pct']:.1f} | {f['sharpe']:.2f} | "
                 f"{c['out_of_sample']['sharpe']:.2f} | {f['trades']} | {f['win_rate_pct']:.0f} | {f['profit_factor']:.2f} |")
    if pk:
        L += ["", f"Cash: {pk['cash_pct']}%", "",
              f"**Portfolio:** net {pk['net_return_pct']:.1f}% (CAGR {pk['cagr_pct']:.1f}%), max DD "
              f"{pk['max_drawdown_pct']:.1f}%, Sharpe {pk['sharpe']:.2f}. Buy & hold of the same assets at the same "
              f"weights: {pk['bh_return_pct']:.1f}%, max DD {pk['bh_max_drawdown_pct']:.1f}%. Period {pk['start'][:10]} -> {pk['end'][:10]}."]
    L += ["", "## Rejected combos", "", "| Combo | Net % | B&H % | Max DD % | Why |", "|---|---|---|---|---|"]
    for c in combos:
        if not c["selected"]:
            f = c["full"]
            L.append(f"| {c['id']} | {f['net_return_pct']:.1f} | {f['bh_return_pct']:.1f} | {f['max_drawdown_pct']:.1f} | "
                     f"{'; '.join(c['rejected_rules'] + ['outlier: ' + x for x in c['outlier_flags']])} |")
    L += ["", "Backtests use mid prices with half the average spread paid per side plus 0.5 bp slippage. "
          "Past results do not predict future returns. Not investment advice."]
    return "\n".join(L) + "\n"


def main(symbols=None, benchmark=None):
    global BENCHMARK
    BENCHMARK = benchmark or BENCHMARK
    symbols = symbols or bars.available_symbols()
    print(f"Researching {symbols} on {TIMEFRAMES} (benchmark: {BENCHMARK})")
    combos = research(symbols)
    if BENCHMARK == "risk_matched":
        for c in combos:
            risk_match(c)
    apply_rules(combos)
    # Final gate: every survivor is re-run on real ticks with latency and must pass again.
    survivors = [c for c in combos if c["selected"]]
    if survivors:
        print(f"Tick-verifying {len(survivors)} survivors (real ticks + latency)...")
        for c in survivors:
            tick_verify(c)
        apply_rules(combos)
    sel = [c for c in combos if c["selected"]]
    allocate(sel)
    pk, eq, bh_eq = portfolio_curve(sel) if sel else ({}, pd.Series(dtype=float), pd.Series(dtype=float))
    report = save(combos, sel, pk, eq, bh_eq)
    print(f"\n{len(sel)} of {len(combos)} combos selected. Report: {report.relative_to(REPO)}")
    for c in sorted(sel, key=lambda c: -c["nav_pct"]):
        print(f"  {c['nav_pct']:6.2f}%  {c['id']}  {c['params']}")
    return sel


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--benchmark", choices=["absolute", "risk_matched"])
    a = ap.parse_args()
    main(a.symbols, a.benchmark)
