"""One bot, every combo: turn the current portfolio into target positions.

For each combo in the portfolio (engine/hot_backtests/portfolio_<benchmark>.json):
  exposure (% of NAV) = %NAV allocation x leverage x signal of the last CLOSED bar (-1/0/+1)
The EA holds one position per combo (magic = Magic + magic_offset), sized when it
opens: lots = exposure x equity / (price x contract), rounded down to the lot step.
This is exactly what engine.portfolio.simulate_account backtests.

Safety stops (exit code 2, nothing is sent):
  - an asset in the portfolio has no equivalent pair in bot.json's available_pairs,
  - bot_id is not set,
  - the newest price bar is older than max_data_age_hours (stale data).

Output: engine/output/orders_latest.json. Read by the MT5 EA (mt5/PortfolioBot.mq5)
or POSTed to the bot's webhook with --send (URL from the env var named in bot.json).

Usage:
    python -m engine.bot              # dry run, writes orders_latest.json
    python -m engine.bot --send       # also POST to the webhook
    python -m engine.bot --check      # only check pair mapping
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import bars, strategies

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "config" / "bot.json"
OUT = ROOT / "output" / "orders_latest.json"


class BotStop(Exception):
    pass


def config() -> dict:
    return json.loads(CFG.read_text())


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_pairs(assets: list[str], cfg: dict | None = None) -> dict[str, str]:
    """asset -> the bot's pair name. Raises BotStop naming every unmapped asset."""
    cfg = cfg or config()
    have = {}
    for p in cfg["available_pairs"]:  # also match without broker suffixes: GOLD.r, US500_cash, XAUUSD-ecn
        have.setdefault(_norm(re.split(r"[._\-]", p)[0]), p)
        have[_norm(p)] = p
    out, missing = {}, []
    for a in assets:
        for cand in [a] + cfg["equivalents"].get(a, []):
            if _norm(cand) in have:
                out[a] = have[_norm(cand)]
                break
        else:
            missing.append(a)
    if missing:
        raise BotStop(
            f"STOP: bot {cfg['bot_id']} has no pair for {', '.join(missing)}. "
            f"Bot pairs: {cfg['available_pairs']}. Add an equivalent pair to the bot (and to "
            f"available_pairs in engine/config/bot.json) or remove the asset from the portfolio."
        )
    return out


def portfolio(cfg: dict) -> dict:
    p = ROOT / "hot_backtests" / f"portfolio_{cfg['benchmark']}.json"
    if not p.exists():
        raise BotStop(f"STOP: no portfolio at {p}. Run: python -m engine.portfolio --benchmark {cfg['benchmark']}")
    return json.loads(p.read_text())


def magic_offset(combo_id: str) -> int:
    """Stable per-combo number; the EA uses Magic + this to own one position per combo."""
    return zlib.crc32(combo_id.encode()) % 90000 + 1


def plan(cfg: dict | None = None, now: datetime | None = None) -> dict:
    cfg = cfg or config()
    now = now or datetime.now(timezone.utc)
    now_utc = pd.Timestamp(now).tz_convert("UTC").tz_localize(None)
    now_server = bars.to_server(pd.DatetimeIndex([now_utc]))[0]
    if cfg["bot_id"] in ("", "SET_ME"):
        raise BotStop("STOP: bot_id is not set in engine/config/bot.json.")
    pf = portfolio(cfg)
    combos = pf["combos"]
    if not combos:
        raise BotStop("STOP: the current portfolio is empty (no combo passed the rules). Holding nothing.")
    pairs = resolve_pairs(sorted({c["asset"] for c in combos}), cfg)

    out, targets, last_h1 = [], {}, None
    for c in combos:
        df = bars.load_bars(c["asset"], c["timeframe"])
        h1_last = bars.load_h1_utc(c["asset"]).index[-1]
        last_h1 = h1_last if last_h1 is None else min(last_h1, h1_last)
        # Like the backtest and an MT5 new-bar EA: only CLOSED bars produce signals.
        if df.index[-1] + bars.TF_DELTA[c["timeframe"]] > now_server:
            df = df.iloc[:-1]
        s = float(strategies.signal(c["strategy"], df, c["params"]).iloc[-1])
        expo = round(c["nav_pct"] * c.get("leverage", 1.0) * s, 2)
        out.append({"combo": c["id"], "pair": pairs[c["asset"]], "magic_offset": magic_offset(c["id"]),
                    "exposure_pct_nav": expo, "signal": s, "nav_pct": c["nav_pct"],
                    "leverage": c.get("leverage", 1.0), "params": c["params"],
                    "signal_bar_server_time": str(df.index[-1])})
        t = targets.setdefault(c["asset"], {"asset": c["asset"], "pair": pairs[c["asset"]], "net_exposure_pct_nav": 0.0})
        t["net_exposure_pct_nav"] = round(t["net_exposure_pct_nav"] + expo, 2)

    age_h = (now_utc - (last_h1 + pd.Timedelta("1h"))).total_seconds() / 3600
    return {
        "bot_id": cfg["bot_id"], "platform": cfg["platform"], "benchmark": pf["benchmark"],
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_mt5": now_utc.strftime("%Y.%m.%d %H:%M"),   # UTC, in the format MQL5 StringToTime reads
        "portfolio_generated_at": pf["generated_at"],
        "last_price_bar_utc": str(last_h1), "data_age_hours": round(age_h, 1),
        "stale": age_h > cfg["max_data_age_hours"],
        "combos": out,
        "net_by_pair": list(targets.values()),
    }


def send(orders: dict, cfg: dict) -> str:
    url = os.environ.get(cfg["webhook_url_env"], "")
    if not url:
        raise BotStop(f"STOP: --send given but env var {cfg['webhook_url_env']} is empty.")
    req = urllib.request.Request(url, data=json.dumps(orders).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return f"webhook HTTP {r.status}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    cfg = config()
    try:
        if a.check:
            m = resolve_pairs(sorted({c["asset"] for c in portfolio(cfg)["combos"]}), cfg)
            print(json.dumps(m, indent=2))
            return 0
        orders = plan(cfg)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(orders, indent=2))
        print(json.dumps(orders, indent=2))
        if orders["stale"]:
            raise BotStop(f"STOP: price data is {orders['data_age_hours']}h old (> {cfg['max_data_age_hours']}h). "
                          "Run python -m engine.livefeed first. Orders written but NOT sent.")
        if a.send:
            print(send(orders, cfg))
        return 0
    except BotStop as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
