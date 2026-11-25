"""A bigger app with a drilldown: drilling does not rerun the app.

The app has a sidebar filter, KPIs and a slow chart (2 s on every full run).
The counters at the top belong to the script. They only change when the whole
script runs, for example when you change the filter. Click through the
drilldown and they stay put, while the "fragment run" counter in the drilldown
goes up and the levels appear instantly.

Run with: streamlit run examples/dashboard_app.py
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING

import sample_data
from streamlit_drilldown import drilldown, selected_point, selected_row

import streamlit as st

if TYPE_CHECKING:
    import pandas as pd

st.set_page_config(layout="wide")

# --- Code in this block runs on every full script run. ---------------------

st.session_state.setdefault("script_runs", 0)
st.session_state.setdefault("fragment_runs", 0)
st.session_state.script_runs += 1

st.sidebar.header("Filters")
product = st.sidebar.selectbox("Product", ["All", "Widget", "Gadget", "Gizmo"])
st.sidebar.caption("Changing a filter reruns the whole script.")
st.sidebar.button("Rerun the whole app")

orders = sample_data.ORDERS
if product != "All":
    orders = orders[orders["product"] == product]

st.title("Sales dashboard")

left, middle, right = st.columns(3)
left.metric("Full script runs", st.session_state.script_runs)
middle.metric("Last full run", datetime.now().strftime("%H:%M:%S"))
right.metric("Revenue", f"{orders['revenue'].sum():,}")

st.subheader("Revenue trend")
with st.spinner("Computing the trend (2 s, on every full run) ..."):
    time.sleep(2)  # Stands in for an expensive computation.
    trend = orders.groupby("month")["revenue"].sum()
st.line_chart(trend, height=150)

# --- The drilldown: only this part reruns when you drill. ------------------

st.subheader("Explore revenue")
st.caption(
    "Select a region, then a country. The counters above do not change. "
    "Only the drilldown reruns, as a fragment."
)


def stamp() -> None:
    """Show that this level was rendered by a fragment run, not a script run."""
    st.session_state.fragment_runs += 1
    st.caption(
        f"Fragment run #{st.session_state.fragment_runs} "
        f"at {datetime.now().strftime('%H:%M:%S')}"
    )


def regions_table(element):
    df = sample_data.revenue_by("region")
    element(df, selection_mode="single-row", hide_index=True)
    stamp()
    return selected_row(df, "region")


def countries_bar(element, region):
    df = sample_data.revenue_by("country", region=region)
    element(sample_data.bar_spec(df, "country"), height=220)
    stamp()
    return selected_point(df["country"].tolist())


def country_orders(element, region, country):
    df: pd.DataFrame = sample_data.orders(region=region, country=country)
    element(df, hide_index=True)
    stamp()


drilldown(
    [
        {
            "title": "Revenue by region",
            "element": st.dataframe,
            "loader": regions_table,
        },
        {"title": "Countries", "element": st.echarts_chart, "loader": countries_bar},
        {"title": "Orders", "element": st.dataframe, "loader": country_orders},
    ],
    key="dashboard",
)
