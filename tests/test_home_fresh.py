"""Filtrul de prospețime pe homepage (72h)."""
from datetime import datetime, timezone

from generator.home_fresh import HOME_MAX_AGE, home_fresh


def test_recent_item_is_fresh():
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    a = {"published": "2026-09-02T10:00:00+00:00"}
    assert home_fresh(a, now=now) is True


def test_old_item_is_stale():
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    a = {"published": "2026-08-25T10:00:00+00:00"}
    assert home_fresh(a, now=now) is False


def test_missing_date_fail_open():
    assert home_fresh({}, now=datetime.now(timezone.utc)) is True


def test_invalid_date_fail_open():
    assert home_fresh({"published": "nu-e-data"}, now=datetime.now(timezone.utc)) is True


def test_boundary_exactly_max_age():
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    a = {"published": (now - HOME_MAX_AGE).isoformat()}
    assert home_fresh(a, now=now) is True


def test_naive_datetime_treated_as_utc():
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    a = {"published": "2026-09-02T11:00:00"}
    assert home_fresh(a, now=now) is True


def test_z_suffix_treated_as_utc():
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    recent = {"published": "2026-01-10T11:00:00Z"}
    old = {"published": "2026-01-07T11:00:00Z"}
    assert home_fresh(recent, now=now) is True
    assert home_fresh(old, now=now) is False


def test_positive_offset_compared_in_utc():
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    a = {"published": "2026-01-07T14:00:00+03:00"}
    # 14:00+03:00 is 11:00 UTC: 73h old, not 70h as ignoring the offset would suggest.
    assert home_fresh(a, now=now) is False


def test_future_item_is_fresh():
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    a = {"published": "2026-01-10T13:00:00+00:00"}
    assert home_fresh(a, now=now) is True
