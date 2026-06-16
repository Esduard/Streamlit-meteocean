import streamlit as st
from _page_template import render_forecast_page

st.set_page_config(page_title="Current Speed Forecast", page_icon="🌊", layout="wide")
render_forecast_page("current_speed")
