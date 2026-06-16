"""
Shared logic for each forecast target page.

Pages call render_forecast_page(target_variable) and nothing else.
All inference is delegated to ForecastingService — no Prophet imports here.
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from meteocean_forecast.domain.forecast_request import ForecastRequest, HorizonValidationError
from meteocean_forecast.features.raw_xlsx_reader import read_raw_xlsx
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

    # --- Exogenous: file upload + feature engineering ---
    if selected_meta.is_exogenous:
        st.subheader("Upload meteocean data")
        uploaded = st.file_uploader(
            "Upload raw hourly meteocean XLSX",
            type=["xlsx"],
            key=f"{target_variable}_upload",
            help="Must contain the standard 40-column meteocean schema.",
        )

        if uploaded is not None:
            try:
                with st.spinner("Reading XLSX…"):
                    raw_df = read_raw_xlsx(uploaded)
                st.success(
                    f"Loaded {len(raw_df):,} rows. "
                    f"Time range: {raw_df['time'].min()} → {raw_df['time'].max()}"
                )
                with st.spinner("Engineering features (PCA, Fourier, …)…"):
                    feature_df = service.prepare_exogenous_features(raw_df, selected_meta)
                st.success(f"Features ready: {len(feature_df):,} rows × {len(feature_df.columns)} columns.")
                st.warning(
                    "**V1 limitation:** PCA and StandardScaler are re-fitted on your uploaded "
                    "data, not on the original training data. Forecast accuracy may differ from "
                    "training performance if the uploaded distribution differs significantly."
                )
                st.session_state[f"{target_variable}_feature_df"] = feature_df
            except Exception as exc:
                st.error(f"Failed to process uploaded file: {exc}")
                st.stop()
        else:
            # Restore from session state if user re-selects same model.
            feature_df = st.session_state.get(f"{target_variable}_feature_df")
            if feature_df is not None:
                st.info(
                    f"Using previously processed feature file ({len(feature_df):,} rows). "
                    "Upload a new file to replace it."
                )

        if feature_df is None:
            st.info("Please upload a raw meteocean XLSX file to continue.")
            st.stop()

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
