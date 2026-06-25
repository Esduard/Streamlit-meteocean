import streamlit as st

from meteocean_forecast import path_utils
from meteocean_forecast.data.uploaded_data_store import UploadedDataStore

st.set_page_config(page_title="Data Upload", page_icon="📤", layout="wide")

_APP_DATA_DIR = path_utils.get_app_data_dir()


@st.cache_resource(show_spinner=False)
def _get_store() -> UploadedDataStore:
    return UploadedDataStore(_APP_DATA_DIR)


def main() -> None:
    st.title("Data Upload")
    st.markdown(
        "Upload raw hourly meteocean `.xlsx` files here, independent of which model "
        "you intend to forecast with. Each file must contain data for exactly **one "
        "platform**. Uploading all of a day's platforms together is encouraged, but "
        "uploading them separately works correctly too."
    )

    store = _get_store()

    latest = store.latest_canonical_timestamp()
    if latest is not None:
        st.caption(f"Latest available data timestamp: **{latest.strftime('%Y-%m-%d %H:%M')}**")
    else:
        st.caption("No data has been uploaded yet.")

    uploaded_files = st.file_uploader(
        "Upload one or more raw hourly meteocean XLSX files",
        type=["xlsx"],
        accept_multiple_files=True,
        help="Each file must contain the standard 40-column meteocean schema for one platform.",
    )

    if uploaded_files:
        if st.button("Process uploads", type="primary"):
            with st.spinner("Ingesting uploaded files…"):
                result = store.ingest_files(uploaded_files)

            for entry in result.accepted:
                st.success(
                    f"**{entry.original_filename}** — platform `{entry.plat_id}`, "
                    f"{entry.row_count:,} rows, days covered: "
                    f"{entry.days_covered[0]} → {entry.days_covered[-1]}"
                )
            for rejection in result.rejected:
                st.error(f"**{rejection.filename}** rejected: {rejection.reason}")

            new_latest = store.latest_canonical_timestamp()
            if new_latest is not None:
                timestamp_str = new_latest.strftime("%Y-%m-%d %H:%M")
                st.info(f"Canonical dataset latest timestamp is now **{timestamp_str}**.")


main()
