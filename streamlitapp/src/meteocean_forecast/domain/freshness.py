"""
Freshness status for the canonical dataset.

`calculate_data_freshness_status` is a pure function mapping the canonical
dataset's latest timestamp (or `None`) to a severity + human-readable message.
`render_data_freshness_warning` is the thin I/O + Streamlit wrapper used on the
forecast page; all testable logic lives in the pure function.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

STALE_DATA_DAYS_GRAY = 30
STALE_DATA_DAYS_YELLOW = 60
STALE_DATA_DAYS_RED = 90


class FreshnessSeverity(Enum):
    OK = "ok"
    NO_DATA = "no_data"
    GRAY = "gray"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True)
class FreshnessStatus:
    severity: FreshnessSeverity
    message: str
    age_days: int | None  # None when there is no canonical dataset yet


def calculate_data_freshness_status(
    latest_timestamp: datetime | None, now: datetime
) -> FreshnessStatus:
    if latest_timestamp is None:
        return FreshnessStatus(
            severity=FreshnessSeverity.NO_DATA,
            message=(
                "No canonical dataset exists yet. Upload meteocean data on the "
                "Data Upload page before running an exogenous forecast."
            ),
            age_days=None,
        )

    age_days = (now - latest_timestamp).days

    if age_days >= STALE_DATA_DAYS_RED:
        return FreshnessStatus(
            severity=FreshnessSeverity.RED,
            message=(
                f"Canonical dataset is {age_days} days old "
                f"(latest data {latest_timestamp:%Y-%m-%d %H:%M}). "
                "Forecasts are very likely unreliable — upload newer data."
            ),
            age_days=age_days,
        )
    if age_days >= STALE_DATA_DAYS_YELLOW:
        return FreshnessStatus(
            severity=FreshnessSeverity.YELLOW,
            message=(
                f"Canonical dataset is {age_days} days old "
                f"(latest data {latest_timestamp:%Y-%m-%d %H:%M}). "
                "Consider uploading newer data before forecasting."
            ),
            age_days=age_days,
        )
    if age_days >= STALE_DATA_DAYS_GRAY:
        return FreshnessStatus(
            severity=FreshnessSeverity.GRAY,
            message=(
                f"Canonical dataset is {age_days} days old "
                f"(latest data {latest_timestamp:%Y-%m-%d %H:%M})."
            ),
            age_days=age_days,
        )
    return FreshnessStatus(
        severity=FreshnessSeverity.OK,
        message=(
            f"Canonical dataset is current "
            f"(latest data {latest_timestamp:%Y-%m-%d %H:%M}, {age_days} days old)."
        ),
        age_days=age_days,
    )


def render_data_freshness_warning() -> None:
    """Read the canonical dataset's latest timestamp and render its freshness.

    Thin wrapper: imports Streamlit and the store lazily so the pure status
    logic in `calculate_data_freshness_status` stays importable and testable
    without Streamlit. Kept unobtrusive — it never blocks page usage.
    """
    import streamlit as st

    from meteocean_forecast import path_utils
    from meteocean_forecast.data.uploaded_data_store import UploadedDataStore

    store = UploadedDataStore(path_utils.get_app_data_dir())
    status = calculate_data_freshness_status(
        store.latest_canonical_timestamp(), datetime.now()
    )

    if status.severity is FreshnessSeverity.RED:
        st.error(status.message)
    elif status.severity is FreshnessSeverity.YELLOW:
        st.warning(status.message)
    elif status.severity in (FreshnessSeverity.GRAY, FreshnessSeverity.NO_DATA):
        st.info(status.message)
    else:
        st.caption(status.message)
