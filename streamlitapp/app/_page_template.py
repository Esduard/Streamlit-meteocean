"""
Shared logic for each forecast target page.

Pages call render_forecast_page(target_variable) and nothing else.
All inference is delegated to ForecastingService — no Prophet imports here.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from meteocean_forecast import path_utils
from meteocean_forecast.data.uploaded_data_store import UploadedDataStore
from meteocean_forecast.domain.forecast_request import ForecastRequest, HorizonValidationError
from meteocean_forecast.domain.freshness import render_data_freshness_warning
from meteocean_forecast.inference.forecasting_service import ForecastingService

_DISPLAY_NAMES = {
    "current_speed": "Current Speed (m/s)",
    "wave_height": "Wave Height (m)",
    "wind_speed": "Wind Speed (m/s)",
}


def _get_service() -> ForecastingService | None:
    service = st.session_state.get("service")
    if service is None:
        st.error("Service not initialised. Please visit the **Home** page first.")
    return service


@st.cache_resource(show_spinner=False)
def _get_uploaded_data_store() -> UploadedDataStore:
    return UploadedDataStore(path_utils.get_app_data_dir())


def _plot_forecast(df: pd.DataFrame, target_variable: str) -> None:
    label = _DISPLAY_NAMES.get(target_variable, target_variable)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat_upper"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            name="Upper bound",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat_lower"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(99, 110, 250, 0.2)",
            showlegend=True,
            name="95% interval",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat"],
            mode="lines",
            line=dict(color="rgb(99, 110, 250)", width=2),
            name="Forecast (yhat)",
        )
    )
    fig.update_layout(
        title=f"{label} — Prophet Forecast",
        xaxis_title="Date / Time",
        yaxis_title=label,
        hovermode="x unified",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_forecast_page(target_variable: str) -> None:
    service = _get_service()
    if service is None:
        return

    label = _DISPLAY_NAMES.get(target_variable, target_variable)
    st.title(f"{label} Forecast")
    render_data_freshness_warning()

    models = service.get_models_for_target(target_variable)
    if not models:
        st.info(
            f"No models are currently available for **{target_variable}**. "
            "Add a trained `.pkl` to `models/{target_variable}/` and restart the app."
        )
        st.stop()

    # --- Model selection ---
    selected_meta = st.selectbox(
        "Select model",
        models,
        format_func=lambda m: m.display_name,
        key=f"{target_variable}_model_select",
    )
    st.caption(f"Model type: **{selected_meta.model_type}**")
    if selected_meta.training_cutoff is not None:
        st.caption(f"Training cutoff: **{selected_meta.training_cutoff.strftime('%Y-%m-%d %H:%M UTC')}**")

    feature_df: pd.DataFrame | None = None

    # --- Exogenous: source raw data from the canonical uploaded dataset ---
    if selected_meta.is_exogenous:
        store = _get_uploaded_data_store()
        latest = store.latest_canonical_timestamp()
        if latest is None:
            st.info(
                "No uploaded meteocean data is available yet. Please upload data on the "
                "**Data Upload** page before forecasting with this model."
            )
            st.stop()

        raw_df = store.load_canonical_dataset()
        try:
            with st.spinner("Engineering features (PCA, Fourier, …)…"):
                feature_df = service.prepare_exogenous_features(raw_df, selected_meta)
        except Exception as exc:
            st.error(f"Failed to engineer features from the canonical dataset: {exc}")
            st.stop()

        st.caption(
            f"Using canonical dataset through **{latest.strftime('%Y-%m-%d %H:%M')}** "
            f"({len(feature_df):,} rows)."
        )
        st.warning(
            "**V1 limitation:** PCA and StandardScaler are re-fitted on the canonical "
            "dataset, not on the original training data. Forecast accuracy may differ from "
            "training performance if the uploaded distribution differs significantly."
        )

    # --- Horizon selection ---
    if selected_meta.is_exogenous:
        max_horizon = len(feature_df)
        default_horizon = min(720, max_horizon)
    else:
        max_horizon = selected_meta.max_univariate_horizon_hours
        default_horizon = 720

    horizon = st.slider(
        "Forecast horizon (hours)",
        min_value=1,
        max_value=max_horizon,
        value=default_horizon,
        step=1,
        key=f"{target_variable}_horizon",
    )

    # --- Run forecast ---
    if st.button("Run Forecast", key=f"{target_variable}_run", type="primary"):
        try:
            if selected_meta.is_exogenous:
                request = ForecastRequest.for_exogenous(selected_meta, feature_df, horizon)
            else:
                request = ForecastRequest.for_univariate(selected_meta, horizon)
        except HorizonValidationError as exc:
            st.error(str(exc))
            st.stop()

        try:
            with st.spinner("Running Prophet forecast…"):
                result_df = service.forecast(request)
            st.session_state[f"{target_variable}_result"] = result_df
        except Exception as exc:
            st.error(f"Forecast failed: {exc}")
            st.stop()

    # --- Display results ---
    result_df = st.session_state.get(f"{target_variable}_result")
    if result_df is not None:
        st.subheader("Forecast Results")
        _plot_forecast(result_df, target_variable)

        with st.expander("Raw forecast table"):
            st.dataframe(result_df, use_container_width=True)

        csv_bytes = result_df.to_csv(index=False).encode()
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=f"{target_variable}_forecast.csv",
            mime="text/csv",
        )
