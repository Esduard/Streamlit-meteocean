"""
Feature engineering for meteocean inference.

Ported from feature_engineering.ipynb (repo root).

V1 limitations (documented here so they are easy to find):
  - PCA (8 components) is refitted on the uploaded file's data, not on the original
    training data. Model accuracy may degrade if the uploaded distribution differs
    significantly from the training set.
    TODO: Serialise the training PCA alongside the .pkl and load it here.

  - StandardScaler (applied in select_and_scale_features) is also refitted on the
    uploaded data for the same reason.
    TODO: Serialise the training scaler alongside the .pkl.

All public functions return new DataFrames and never mutate the input.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGNITUDE_MAP: dict[str, str] = {
    "atm_wnd_dir_10m": "atm_wnd_spd_10m",
    "wav_dm": "wav_hs",
    "wav_ww_dm": "wav_ww_hs",
    "wav_sw_dm": "wav_sw_hs",
    "wav_pk1_dm": "wav_pk1_hs",
    "wav_pk2_dm": "wav_pk2_hs",
    "sw_cur_dir": "sw_cur_spd",
}

REGIME_HEADINGS: dict[str, float] = {
    "NBC": 315.0,
    "SEC": 270.0,
    "NECC": 90.0,
    "EUC": 90.0,
}

# Columns used as input for PCA (mirrors the notebook's features_for_pca list).
PCA_INPUT_COLS: list[str] = [
    "latitude",
    "longitude",
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
    "sw_cur_dir",
    "atm_wnd_dir_10m_u",
    "atm_wnd_dir_10m_v",
    "wav_dm_u",
    "wav_dm_v",
    "wav_ww_dm_u",
    "wav_ww_dm_v",
    "wav_sw_dm_u",
    "wav_sw_dm_v",
    "wav_pk1_dm_u",
    "wav_pk1_dm_v",
    "wav_pk2_dm_u",
    "wav_pk2_dm_v",
    "sw_cur_dir_u",
    "sw_cur_dir_v",
    "wave_energy",
    "swell_energy",
    "windwave_energy",
    "wind_current_alignment",
]

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _dir_to_uv(
    direction_deg: pd.Series, magnitude: pd.Series
) -> tuple[pd.Series, pd.Series]:
    theta = np.deg2rad(direction_deg)
    u = -magnitude * np.sin(theta)
    v = -magnitude * np.cos(theta)
    return u, v


def _add_uv_components(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for dir_col, mag_col in MAGNITUDE_MAP.items():
        if dir_col not in df.columns:
            warnings.warn(f"Direction column '{dir_col}' not found; skipping u/v for it.", stacklevel=3)
            continue
        if mag_col not in df.columns:
            warnings.warn(f"Magnitude column '{mag_col}' not found; skipping u/v for it.", stacklevel=3)
            continue
        u, v = _dir_to_uv(df[dir_col], df[mag_col])
        df[f"{dir_col}_u"] = u
        df[f"{dir_col}_v"] = v
    return df


def _add_energy_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["wave_energy"] = df["wav_hs"] ** 2
    df["swell_energy"] = df["wav_sw_hs"] ** 2
    df["windwave_energy"] = df["wav_ww_hs"] ** 2
    df["wind_current_alignment"] = (
        df["atm_wnd_dir_10m_u"] * df["sw_cur_dir_u"]
        + df["atm_wnd_dir_10m_v"] * df["sw_cur_dir_v"]
    )
    return df


def _add_pca_features(df: pd.DataFrame, n_components: int = 8) -> pd.DataFrame:
    # TODO: Load pre-fitted PCA from the model pkl directory instead of refitting here.
    df = df.copy()
    available_cols = [c for c in PCA_INPUT_COLS if c in df.columns]
    if len(available_cols) < n_components:
        warnings.warn(
            f"Only {len(available_cols)} PCA input columns found; need at least {n_components}. "
            "PCA features will be skipped.",
            stacklevel=3,
        )
        for i in range(1, n_components + 1):
            df[f"PCA_{i}"] = np.nan
        return df

    valid_mask = df[available_cols].notna().all(axis=1)
    X = df.loc[valid_mask, available_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    pca_df = pd.DataFrame(
        X_pca,
        columns=[f"PCA_{i + 1}" for i in range(n_components)],
        index=df.index[valid_mask],
    )
    for col in pca_df.columns:
        df[col] = np.nan
        df.loc[valid_mask, col] = pca_df[col]

    return df


def _add_seasonal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df["month"] = df["time"].dt.month
    df["day_of_year"] = df["time"].dt.dayofyear

    df["annual_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["annual_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)
    df["annual_phase"] = df["day_of_year"] / 365.0

    df = pd.get_dummies(df, columns=["month"], prefix="month")

    # Ensure all 12 month dummy columns are present (some months may be absent in small files).
    for m in range(1, 13):
        col = f"month_{m}"
        if col not in df.columns:
            df[col] = 0
    # Cast month dummies to int (get_dummies may produce bool in newer pandas).
    month_cols = [f"month_{m}" for m in range(1, 13)]
    df[month_cols] = df[month_cols].astype(int)

    # Southern-hemisphere seasons.
    df["is_summer"] = df["time"].dt.month.isin([12, 1, 2]).astype(int)
    df["is_autumn"] = df["time"].dt.month.isin([3, 4, 5]).astype(int)
    df["is_winter"] = df["time"].dt.month.isin([6, 7, 8]).astype(int)
    df["is_spring"] = df["time"].dt.month.isin([9, 10, 11]).astype(int)

    return df


def _classify_regime(direction_deg: float) -> str:
    d = direction_deg % 360
    if 300 <= d <= 330:
        return "NBC"
    if 250 <= d <= 290:
        return "SEC"
    if 80 <= d <= 100:  # EUC checked before NECC (narrower band)
        return "EUC"
    if 70 <= d <= 110:
        return "NECC"
    return "Other"


def _alignment_score(direction_deg: float, regime_heading: float) -> float:
    ang_diff = np.deg2rad((direction_deg - regime_heading) % 360)
    return float(np.cos(ang_diff))


def _soft_membership(direction: float, mean_deg: float, kappa: float = 3.0) -> float:
    diff = np.deg2rad((direction - mean_deg) % 360)
    return float(np.exp(kappa * np.cos(diff)))


def _add_directional_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["wind_dir"] = df["atm_wnd_dir_10m"] % 360
    df["wave_dir"] = df["wav_dm"] % 360
    df["current_dir"] = df["sw_cur_dir"] % 360

    df["wind_regime"] = df["wind_dir"].apply(_classify_regime)
    df["wave_regime"] = df["wave_dir"].apply(_classify_regime)
    df["current_regime"] = df["current_dir"].apply(_classify_regime)

    df = pd.get_dummies(df, columns=["wind_regime", "wave_regime", "current_regime"])

    # Ensure expected one-hot columns exist (regime may never appear in small datasets).
    regime_cols = {
        "wind_regime": ["NBC", "NECC", "Other", "SEC", "EUC"],
        "wave_regime": ["NBC", "NECC", "Other", "SEC", "EUC"],
        "current_regime": ["NBC", "NECC", "Other", "SEC", "EUC"],
    }
    for prefix, labels in regime_cols.items():
        for label in labels:
            col = f"{prefix}_{label}"
            if col not in df.columns:
                df[col] = 0
            df[col] = df[col].astype(int)

    # Alignment scores (cosine-based, continuous).
    for feature, dircol in [("wind", "wind_dir"), ("wave", "wave_dir"), ("current", "current_dir")]:
        for regime, heading in REGIME_HEADINGS.items():
            df[f"{feature}_align_{regime}"] = df[dircol].apply(
                lambda x, h=heading: _alignment_score(x, h)
            )

    # Soft membership (von Mises kernel).
    for feature, dircol in [("wind", "wind_dir"), ("wave", "wave_dir"), ("current", "current_dir")]:
        for regime, heading in REGIME_HEADINGS.items():
            df[f"{feature}_prob_{regime}"] = df[dircol].apply(
                lambda x, h=heading: _soft_membership(x, h)
            )

    return df


def _add_fourier_feature(
    df: pd.DataFrame,
    value_col: str = "sw_cur_spd",
    time_col: str = "time",
    period_days: float = 365.25,
    n_harmonics: int = 32,
    include_trend: bool = True,
) -> pd.DataFrame:
    if value_col not in df.columns or df[value_col].isna().all():
        raise ValueError(
            f"Column '{value_col}' is required for the Fourier seasonal feature but is missing "
            "or all-NaN. The exogenous model needs sw_cur_spd in the uploaded file to compute "
            "this feature."
        )

    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")

    t0 = df[time_col].iloc[0]

    def _to_days(t: pd.Series) -> pd.Series:
        return (t - t0).dt.total_seconds() / 86400.0

    def _design_matrix(t_array: np.ndarray) -> np.ndarray:
        cols = [np.ones(len(t_array))]
        if include_trend:
            cols.append(t_array)
        for k in range(1, n_harmonics + 1):
            omega = 2.0 * np.pi * k / period_days
            cols.append(np.sin(omega * t_array))
            cols.append(np.cos(omega * t_array))
        return np.vstack(cols).T

    valid = df[time_col].notna() & df[value_col].notna()
    t_vals = _to_days(df.loc[valid, time_col]).values
    y_vals = df.loc[valid, value_col].values

    A = _design_matrix(t_vals)
    coeffs, *_ = np.linalg.lstsq(A, y_vals, rcond=None)

    output_col = f"{value_col}_fourier"
    df[output_col] = np.nan
    all_valid = df[time_col].notna()
    t_all = _to_days(df.loc[all_valid, time_col]).values
    df.loc[all_valid, output_col] = _design_matrix(t_all) @ coeffs

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def engineer_features(
    raw_df: pd.DataFrame,
    platform: str | None = None,  # reserved for future per-platform calibration
) -> pd.DataFrame:
    """
    Transform a raw meteocean DataFrame (output of read_raw_xlsx) into an
    engineered feature DataFrame with a Prophet-compatible 'ds' column.

    Steps: uv components → energy features → PCA → seasonal → directional → Fourier.
    Returns a new DataFrame; input is never mutated.
    """
    df = raw_df.copy()

    df = _add_uv_components(df)
    df = _add_energy_features(df)
    df = _add_pca_features(df)
    df = _add_seasonal_features(df)
    df = _add_directional_features(df)
    df = _add_fourier_feature(df)

    # Prophet requires a 'ds' column with datetime values.
    df = df.rename(columns={"time": "ds"})
    df["ds"] = pd.to_datetime(df["ds"])

    return df


def select_and_scale_features(
    engineered_df: pd.DataFrame,
    feature_name_map: list[str],
) -> pd.DataFrame:
    """
    Select the named features from engineered_df, apply StandardScaler, and
    rename columns to feature_0 … feature_N (the names expected by Prophet).

    Returns a new DataFrame with 'ds' plus the scaled feature columns.

    V1 limitation: scaler is fitted on the uploaded data, not the training data.
    TODO: load the training scaler from alongside the pkl.
    """
    missing = [f for f in feature_name_map if f not in engineered_df.columns]
    if missing:
        raise ValueError(
            f"engineered_df is missing the following required feature columns: {missing}"
        )

    X = engineered_df[feature_name_map].values.astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    feature_cols = [f"feature_{i}" for i in range(len(feature_name_map))]
    result = pd.DataFrame(X_scaled, columns=feature_cols, index=engineered_df.index)
    result.insert(0, "ds", engineered_df["ds"].values)
    return result
