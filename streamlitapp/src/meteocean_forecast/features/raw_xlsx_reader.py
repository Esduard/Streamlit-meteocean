from __future__ import annotations

import warnings
from pathlib import Path
from typing import IO

import pandas as pd

EXPECTED_COLUMNS: list[str] = [
    "time",
    "latitude",
    "longitude",
    "plat_id",
    "atm_wnd_spd_10m",
    "atm_wnd_dir_10m",
    "wav_hs",
    "wav_hmax",
    "wav_tp",
    "wav_tmm10",
    "wav_tm01",
    "wav_tm02",
    "wav_hmaxt",
    "wav_dm",
    "wav_ww_hs",
    "wav_ww_tp",
    "wav_ww_tmm10",
    "wav_ww_tm01",
    "wav_ww_tm02",
    "wav_ww_dm",
    "wav_sw_hs",
    "wav_sw_tp",
    "wav_sw_tmm10",
    "wav_sw_tm01",
    "wav_sw_tm02",
    "wav_sw_dm",
    "wav_pk1_hs",
    "wav_pk1_tp",
    "wav_pk1_tmm10",
    "wav_pk1_tm01",
    "wav_pk1_tm02",
    "wav_pk1_dm",
    "wav_pk2_hs",
    "wav_pk2_tp",
    "wav_pk2_tmm10",
    "wav_pk2_tm01",
    "wav_pk2_tm02",
    "wav_pk2_dm",
    "sw_cur_spd",
    "sw_cur_dir",
]

# Long column names used in one platform file that must be normalised.
_RENAME_MAP: dict[str, str] = {
    "atm_wnd_spd_10m (vel de vento)": "atm_wnd_spd_10m",
    "wav_hs (altura de onda)": "wav_hs",
    "sw_cur_spd (vel. Corrente)": "sw_cur_spd",
}


def read_raw_xlsx(path: Path | str | IO) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")

    # Normalise long column names (idempotent if already short).
    df = df.rename(columns=_RENAME_MAP, errors="ignore")

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Uploaded file is missing required columns: {missing}")

    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    nat_count = df["time"].isna().sum()
    if nat_count / len(df) > 0.05:
        raise ValueError(
            f"{nat_count} of {len(df)} timestamps could not be parsed "
            f"({100 * nat_count / len(df):.1f}%). Check the 'time' column format."
        )

    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    # Warn about unexpected hourly gaps (does not raise).
    if len(df) > 1:
        diffs = df["time"].diff().dropna()
        expected = pd.Timedelta("1h")
        irregular = diffs[diffs != expected]
        if not irregular.empty:
            warnings.warn(
                f"Found {len(irregular)} timestamp gaps that are not exactly 1 hour. "
                "Feature engineering assumes hourly data.",
                stacklevel=2,
            )

    return df
