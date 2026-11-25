"""A widget as the first level: pills -> bar chart -> DataFrame.

A level can be any element that returns a value. For `st.pills` the value is
the selection, so the loader returns the `value` resolver.

Run with: streamlit run examples/pills_bar_table.py
"""

import sample_data

import streamlit as st
from streamlit_drilldown import drilldown, selected_point, value


def region_pills(element):
    element("Region", list(sample_data.COUNTRIES), selection_mode="single")
    return value


def countries_bar(element, region):
    df = sample_data.revenue_by("country", region=region)
    element(sample_data.bar_spec(df, "country"), height=300)
    return selected_point(df["country"].tolist())


def country_orders(element, region, country):
    element(sample_data.orders(region=region, country=country), hide_index=True)


st.title("Pills → bar chart → table")

drilldown(
    [
        {"title": "Pick a region", "element": st.pills, "loader": region_pills},
        {"title": "Countries", "element": st.echarts_chart, "loader": countries_bar},
        {"title": "Orders", "element": st.dataframe, "loader": country_orders},
    ],
    key="pills-bar-table",
)
