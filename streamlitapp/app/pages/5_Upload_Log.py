import pandas as pd
import streamlit as st

from meteocean_forecast import path_utils
from meteocean_forecast.data.uploaded_data_store import UploadedDataStore

st.set_page_config(page_title="Upload Log", page_icon="📜", layout="wide")

_APP_DATA_DIR = path_utils.get_app_data_dir()


@st.cache_resource(show_spinner=False)
def _get_store() -> UploadedDataStore:
    return UploadedDataStore(_APP_DATA_DIR)


def main() -> None:
    st.title("Upload Log")
    st.markdown(
        "A read-only history of every raw meteocean file ingested into the canonical "
        "dataset. To upload new data, use the **Data Upload** page."
    )

    store = _get_store()

    latest = store.latest_canonical_timestamp()
    if latest is not None:
        st.caption(f"Latest available data timestamp: **{latest.strftime('%Y-%m-%d %H:%M')}**")
    else:
        st.caption("No data has been uploaded yet.")

    entries = store.upload_log()
    if not entries:
        st.info("No uploads have been recorded yet. Upload data on the **Data Upload** page.")
        return

    table = pd.DataFrame(
        [
            {
                "Filename": entry.original_filename,
                "Platform": entry.plat_id,
                "Days covered": ", ".join(entry.days_covered),
                "Upload time": entry.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                "Rows": entry.row_count,
            }
            for entry in entries
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)


main()
