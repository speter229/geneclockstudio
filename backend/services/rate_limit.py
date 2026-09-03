"""Per-user sliding-window rate limiting for endpoints that can leak secrets.

The built-in clocks' CpG lists are proprietary. Several endpoints are, in a weak
sense, oracles about those lists:

* ``/predictions/calculate_percent/`` reports how much of a clock a submitted CpG
  set covers - bucketed, but repeated probing of hand-picked subsets still narrows
  the list down.
* ``/predictions/predict/`` returns an age that only changes when a submitted CpG
  is actually used by the clock, so a caller can test candidate sites one at a time.

Neither can be closed by making the response coarser without breaking the feature,
so both are additionally rate limited: legitimate use is a handful of calls per
loaded dataset, while enumerating the ~450k sites on an EPIC array needs orders of
magnitude more. Limits are per authenticated user and per process.
"""

import logging
import threading
import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException

# Stop tracking users that have not called in this long, so a long-running server
# does not accumulate an unbounded number of per-user deques.
IDLE_EVICTION_SECONDS = 24 * 3600


class RateLimiter:
    """Sliding-window limiter: at most ``max_calls`` per ``window_seconds`` per key."""

    def __init__(self, name: str, max_calls: int, window_seconds: int):
        self.name = name
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _evict_idle(self, now: float):
        """Drops keys whose most recent call is older than IDLE_EVICTION_SECONDS."""
        stale = [
            key for key, calls in self._calls.items()
            if not calls or now - calls[-1] > IDLE_EVICTION_SECONDS
        ]
        for key in stale:
            del self._calls[key]

    def check(self, key: str):
        """Records a call for ``key``.

        Raises:
            HTTPException: 429 if ``key`` already used up its quota for the window.
        """
        now = time.time()
        with self._lock:
            if len(self._calls) > 1000:
                self._evict_idle(now)

            calls = self._calls.setdefault(key, deque())
            while calls and now - calls[0] > self.window_seconds:
                calls.popleft()

            if len(calls) >= self.max_calls:
                # Log it: a user hitting this is either scripting the UI or probing.
                logging.warning(
                    "Rate limit '%s' hit by user %s (%d calls / %ds)",
                    self.name, key, self.max_calls, self.window_seconds,
                )
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                )

            calls.append(now)

    def reset(self):
        """Clears all recorded calls. For tests."""
        with self._lock:
            self._calls.clear()
