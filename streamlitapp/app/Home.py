import pandas as pd
import streamlit as st

from meteocean_forecast import path_utils
from meteocean_forecast.inference.forecasting_service import ForecastingService

st.set_page_config(
    page_title="Meteocean Forecasting",
    page_icon="🌊",
    layout="wide",
)

_MODELS_DIR = path_utils.get_models_dir()
_TARGETS = ["current_speed", "wave_height", "wind_speed"]


@st.cache_resource(show_spinner="Loading models from disk…")
def _load_service() -> ForecastingService:
    return ForecastingService(_MODELS_DIR)


def main() -> None:
    st.title("Meteocean Forecasting App")
    st.markdown(
        "Hourly forecasts of **current speed**, **wave height**, and **wind speed** "
        "using Prophet models trained on ERA5 / CMEMS data."
    )

    service = _load_service()
    st.session_state["service"] = service

    st.header("Available Models")

    rows = []
    for meta in service.all_metadata:
        rows.append(
            {
                "Target Variable": meta.target_variable,
                "Model Type": meta.model_type,
                "Model Name": meta.display_name,
                "Required Features": len(meta.required_features),
                "Max Horizon (h)": str(meta.max_univariate_horizon_hours)
                if not meta.is_exogenous
                else "depends on uploaded file",
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No models found in the models/ directory.")

    with st.expander("About model types"):
        st.markdown(
            """
**Univariate models**
- Do not require an uploaded feature file.
- Generate future timestamps internally.
- Forecast horizon up to **8 760 hours** (1 year).

**Exogenous models**
- Require an XLSX file with raw hourly meteocean data.
- The uploaded file is transformed through the full feature engineering pipeline.
- Forecast horizon is limited by the number of rows in the processed file.

---

**V1 limitations**
- PCA (8 components) is re-fitted on the uploaded data, not on the original training data.
- The StandardScaler is also re-fitted on the uploaded data.
  Predictions may differ from training accuracy if the uploaded distribution differs
  significantly from the training set.
  *TODO: serialise the training PCA and scaler alongside the `.pkl` file.*

- Models are loaded from trusted local `.pkl` files.
  *TODO: migrate to Prophet JSON serialisation to remove the `sys.path` dependency.*
            """
        )

    st.caption("Navigate to a target variable page in the sidebar to run a forecast.")


main()
