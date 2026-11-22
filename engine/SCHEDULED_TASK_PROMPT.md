# Scheduled task: Portfolio Bot run

This is the prompt the scheduled task runs. It automates the whole Portfolio Prompt for ONE bot.

---

You are running the Portfolio Bot for repository CarlosSilva1/DataFeedPrice.

1. Get the code. If the repo is not already in your working directory, clone it. Check out branch
   `claude/sleepy-hypatia-xi4g3r` (the branch the MT5 EA reads orders from) and pull it.
   Run `pip install -r engine/requirements.txt`.
2. Update prices: `python -m engine.livefeed`. If it fails because datafeed.dukascopy.com is blocked,
   say so in your final message; the bot step below will then STOP on stale data, which is correct.
3. Rebuild the portfolio when it is older than 7 days (check `generated_at` in
   `engine/hot_backtests/portfolio_<benchmark>.json`, benchmark from `engine/config/bot.json`) or missing:
   `python -m engine.portfolio --benchmark <benchmark>`.
   Rules it applies: beats buy & hold over the same period, max drawdown < 50%, too-good-to-be-true
   outliers removed, %NAV sized by risk/reward; every selected combo is saved to Hot Backtests
   (`engine/hot_backtests/hot_backtests.json`).
4. Check pairs: `python -m engine.bot --check`. If it exits with code 2, STOP. Tell the user exactly
   which asset has no equivalent pair on their bot (the message names it). Do not send orders.
5. Produce orders: `python -m engine.bot` (add `--send` only if the BOT_WEBHOOK_URL env var is set).
   Exit code 2 = STOP: report the message verbatim and do not trade.
6. Commit `engine/hot_backtests/`, `engine/output/orders_latest.json` and `engine/data/bars/*_live.csv.gz`
   with message "Bot run <UTC time>" and push to `claude/sleepy-hypatia-xi4g3r`
   (`git push -u origin claude/sleepy-hypatia-xi4g3r`, retry up to 4 times on network errors).
   The MT5 EA picks the orders up from there.
7. Final message (short): bot ID, per pair target %NAV and the combos behind it, whether the
   portfolio was rebuilt (and what changed), any STOP and why. Never change engine rules or
   config on your own.
