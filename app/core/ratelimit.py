"""限流 (SPEC §4.5): slowapi 单一 Limiter 实例, 被 routes 复用.

仅挂在 auth/写端点 (bids/clearing/forecast/backtest). CORS allowlist + 限流 见 main.py.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
