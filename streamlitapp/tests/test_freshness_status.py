"""Pure-function tests for calculate_data_freshness_status."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from meteocean_forecast.domain.freshness import (
    FreshnessSeverity,
    calculate_data_freshness_status,
)

_NOW = datetime(2026, 6, 24, 12, 0, 0)


def _status_for_age(age_days: int) -> FreshnessSeverity:
    latest = _NOW - timedelta(days=age_days)
    return calculate_data_freshness_status(latest, _NOW).severity


def test_none_timestamp_is_no_data():
    status = calculate_data_freshness_status(None, _NOW)
    assert status.severity is FreshnessSeverity.NO_DATA
    assert status.age_days is None


def test_fresh_timestamp_is_ok():
    assert _status_for_age(0) is FreshnessSeverity.OK
    assert _status_for_age(10) is FreshnessSeverity.OK


@pytest.mark.parametrize(
    "age_days, expected",
    [
        (29, FreshnessSeverity.OK),
        (30, FreshnessSeverity.GRAY),
        (31, FreshnessSeverity.GRAY),
        (59, FreshnessSeverity.GRAY),
        (60, FreshnessSeverity.YELLOW),
        (61, FreshnessSeverity.YELLOW),
        (89, FreshnessSeverity.YELLOW),
        (90, FreshnessSeverity.RED),
        (91, FreshnessSeverity.RED),
    ],
)
def test_boundaries(age_days: int, expected: FreshnessSeverity):
    assert _status_for_age(age_days) is expected


def test_age_days_is_reported():
    latest = _NOW - timedelta(days=45)
    status = calculate_data_freshness_status(latest, _NOW)
    assert status.age_days == 45
