"""Strategy library. Each strategy maps a bar DataFrame to a target position
series in {-1, 0, +1}, decided on the bar's close and held from the next bar.

GRID lists the parameter sets the optimizer tries for each strategy.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _side(sig: pd.Series, mode: str) -> pd.Series:
    return sig.clip(lower=0) if mode == "long" else sig


def _hold(entry_long, exit_long, entry_short=None, exit_short=None) -> pd.Series:
    """Stateful position from entry/exit boolean series."""
    el, xl = entry_long.to_numpy(), exit_long.to_numpy()
    es = entry_short.to_numpy() if entry_short is not None else np.zeros_like(el)
    xs = exit_short.to_numpy() if exit_short is not None else np.zeros_like(el)
    pos = np.zeros(len(el))
    p = 0
    for i in range(len(el)):
        if p == 1 and xl[i]:
            p = 0
        elif p == -1 and xs[i]:
            p = 0
        if p == 0:
            if el[i]:
                p = 1
            elif es[i]:
                p = -1
        pos[i] = p
    return pd.Series(pos, index=entry_long.index)


def ma_cross(df, fast, slow, mode):
    c = df.close
    return _side(np.sign(_ema(c, fast) - _ema(c, slow)), mode)


def trend_ema(df, n, mode):
    c = df.close
    return _side(np.sign(c - _ema(c, n)), mode)


def donchian(df, n, mode):
    hi = df.high.rolling(n).max().shift(1)
    lo = df.low.rolling(n).min().shift(1)
    m = max(2, n // 2)
    xhi = df.high.rolling(m).max().shift(1)
    xlo = df.low.rolling(m).min().shift(1)
    c = df.close
    if mode == "long":
        return _hold(c > hi, c < xlo)
    return _hold(c > hi, c < xlo, c < lo, c > xhi)


def macd(df, fast, slow, signal, mode):
    m = _ema(df.close, fast) - _ema(df.close, slow)
    return _side(np.sign(m - _ema(m, signal)), mode)


def rsi_reversion(df, n, lo, hi, mode):
    r = _rsi(df.close, n)
    if mode == "long":
        return _hold(r < lo, r > 50)
    return _hold(r < lo, r > 50, r > hi, r < 50)


def bollinger_reversion(df, n, k, mode):
    c = df.close
    ma, sd = c.rolling(n).mean(), c.rolling(n).std()
    if mode == "long":
        return _hold(c < ma - k * sd, c > ma)
    return _hold(c < ma - k * sd, c > ma, c > ma + k * sd, c < ma)


def trend_pullback(df, trend, n, lo, mode):
    """Buy RSI dips only while price is above the long trend EMA."""
    c = df.close
    up = c > _ema(c, trend)
    r = _rsi(c, n)
    if mode == "long":
        return _hold(up & (r < lo), (r > 60) | ~up)
    dn = ~up
    return _hold(up & (r < lo), (r > 60) | dn, dn & (r > 100 - lo), (r < 40) | up)


STRATEGIES = {
    "ma_cross": ma_cross,
    "trend_ema": trend_ema,
    "donchian": donchian,
    "macd": macd,
    "rsi_reversion": rsi_reversion,
    "bollinger_reversion": bollinger_reversion,
    "trend_pullback": trend_pullback,
}

_MODES = ["long", "long_short"]


def _g(**kw):
    keys = list(kw)
    return [dict(zip(keys, v)) for v in itertools.product(*kw.values())]


GRID = {
    "ma_cross": [p for p in _g(fast=[5, 10, 20, 50], slow=[50, 100, 200], mode=_MODES) if p["fast"] < p["slow"]],
    "trend_ema": _g(n=[20, 50, 100, 200], mode=_MODES),
    "donchian": _g(n=[20, 55, 100], mode=_MODES),
    "macd": _g(fast=[8, 12], slow=[26, 50], signal=[9], mode=_MODES),
    "rsi_reversion": _g(n=[2, 14], lo=[10, 30], hi=[70, 90], mode=_MODES),
    "bollinger_reversion": _g(n=[20, 50], k=[2.0, 2.5], mode=_MODES),
    "trend_pullback": _g(trend=[100, 200], n=[2, 14], lo=[10, 30], mode=_MODES),
}


def signal(name: str, df: pd.DataFrame, params: dict) -> pd.Series:
    return STRATEGIES[name](df, **params).fillna(0)
