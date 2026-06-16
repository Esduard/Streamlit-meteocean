"""Shared fixtures for all tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_raw_df(n_rows: int = 200, start: str = "2022-01-01") -> pd.DataFrame:
    """Return a minimal synthetic DataFrame matching the 40-column raw schema."""
    times = pd.date_range(start, periods=n_rows, freq="h")
    rng = np.random.default_rng(42)

    data: dict = {
        "time": times,
        "latitude": rng.uniform(-5, 5, n_rows),
        "longitude": rng.uniform(-50, -40, n_rows),
        "plat_id": "TEST",
        "atm_wnd_spd_10m": rng.uniform(0, 15, n_rows),
        "atm_wnd_dir_10m": rng.uniform(0, 360, n_rows),
        "wav_hs": rng.uniform(0.5, 4, n_rows),
        "wav_hmax": rng.uniform(0.6, 5, n_rows),
        "wav_tp": rng.uniform(4, 14, n_rows),
        "wav_tmm10": rng.uniform(4, 14, n_rows),
        "wav_tm01": rng.uniform(4, 14, n_rows),
        "wav_tm02": rng.uniform(4, 14, n_rows),
        "wav_hmaxt": rng.uniform(4, 14, n_rows),
        "wav_dm": rng.uniform(0, 360, n_rows),
        "wav_ww_hs": rng.uniform(0.1, 2, n_rows),
        "wav_ww_tp": rng.uniform(3, 10, n_rows),
        "wav_ww_tmm10": rng.uniform(3, 10, n_rows),
        "wav_ww_tm01": rng.uniform(3, 10, n_rows),
        "wav_ww_tm02": rng.uniform(3, 10, n_rows),
        "wav_ww_dm": rng.uniform(0, 360, n_rows),
        "wav_sw_hs": rng.uniform(0.1, 2, n_rows),
        "wav_sw_tp": rng.uniform(5, 15, n_rows),
        "wav_sw_tmm10": rng.uniform(5, 15, n_rows),
        "wav_sw_tm01": rng.uniform(5, 15, n_rows),
        "wav_sw_tm02": rng.uniform(5, 15, n_rows),
        "wav_sw_dm": rng.uniform(0, 360, n_rows),
        "wav_pk1_hs": rng.uniform(0.1, 2, n_rows),
        "wav_pk1_tp": rng.uniform(4, 14, n_rows),
        "wav_pk1_tmm10": rng.uniform(4, 14, n_rows),
        "wav_pk1_tm01": rng.uniform(4, 14, n_rows),
        "wav_pk1_tm02": rng.uniform(4, 14, n_rows),
        "wav_pk1_dm": rng.uniform(0, 360, n_rows),
        "wav_pk2_hs": rng.uniform(0.1, 2, n_rows),
        "wav_pk2_tp": rng.uniform(4, 14, n_rows),
        "wav_pk2_tmm10": rng.uniform(4, 14, n_rows),
        "wav_pk2_tm01": rng.uniform(4, 14, n_rows),
        "wav_pk2_tm02": rng.uniform(4, 14, n_rows),
        "wav_pk2_dm": rng.uniform(0, 360, n_rows),
        "sw_cur_spd": rng.uniform(0, 1.5, n_rows),
        "sw_cur_dir": rng.uniform(0, 360, n_rows),
    }
    return pd.DataFrame(data)


@pytest.fixture()
def raw_df() -> pd.DataFrame:
    return _make_raw_df()


@pytest.fixture()
def raw_df_december() -> pd.DataFrame:
    """10 rows starting in December — for southern-hemisphere season tests."""
    return _make_raw_df(n_rows=10, start="2022-12-01")
