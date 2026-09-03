"""Tests for the per-user sliding-window rate limiter that protects the
clock-feature oracles (see backend/services/rate_limit.py)."""

import pytest
from fastapi import HTTPException

from backend.services.rate_limit import RateLimiter


def test_allows_calls_up_to_the_limit():
    limiter = RateLimiter("test", max_calls=3, window_seconds=3600)
    for _ in range(3):
        limiter.check("alice")  # must not raise


def test_blocks_the_call_over_the_limit():
    limiter = RateLimiter("test", max_calls=2, window_seconds=3600)
    limiter.check("alice")
    limiter.check("alice")
    with pytest.raises(HTTPException) as exc:
        limiter.check("alice")
    assert exc.value.status_code == 429


def test_limit_is_per_user():
    """One user exhausting their quota must not lock anybody else out."""
    limiter = RateLimiter("test", max_calls=1, window_seconds=3600)
    limiter.check("alice")
    with pytest.raises(HTTPException):
        limiter.check("alice")
    limiter.check("bob")  # unaffected


def test_calls_outside_the_window_are_forgotten(monkeypatch):
    limiter = RateLimiter("test", max_calls=2, window_seconds=60)
    now = [1000.0]
    monkeypatch.setattr("backend.services.rate_limit.time.time", lambda: now[0])

    limiter.check("alice")
    limiter.check("alice")
    with pytest.raises(HTTPException):
        limiter.check("alice")

    now[0] += 61  # the window has passed
    limiter.check("alice")


def test_idle_users_are_evicted(monkeypatch):
    """The per-user table must not grow without bound on a long-running server."""
    from backend.services import rate_limit

    limiter = RateLimiter("test", max_calls=5, window_seconds=60)
    now = [1000.0]
    monkeypatch.setattr("backend.services.rate_limit.time.time", lambda: now[0])

    for i in range(1001):
        limiter.check(f"user_{i}")
    assert len(limiter._calls) > 1000

    now[0] += rate_limit.IDLE_EVICTION_SECONDS + 1
    limiter.check("late_user")
    assert len(limiter._calls) == 1
