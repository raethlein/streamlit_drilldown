"""A selectbox level: DataFrame -> selectbox -> DataFrame.

A widget that always has a value, such as `st.selectbox`, needs `index=None`.
Otherwise it would drill down on its own as soon as it appears.

Run with: streamlit run examples/table_selectbox_table.py
"""

import sample_data

import streamlit as st
from streamlit_drilldown import drilldown, selected_row, value


def regions_table(element):
    df = sample_data.revenue_by("region")
    element(df, selection_mode="single-row", hide_index=True)
    return selected_row(df, "region")


def country_selectbox(element, region):
    countries = sample_data.COUNTRIES[region]
    element(f"Country in {region}", countries, index=None)
    return value


def country_orders(element, region, country):
    element(sample_data.orders(region=region, country=country), hide_index=True)


st.title("Table → selectbox → table")

drilldown(
    [
        {"title": "Revenue by region", "element": st.dataframe, "loader": regions_table},
        {"title": "Pick a country", "element": st.selectbox, "loader": country_selectbox},
        {"title": "Orders", "element": st.dataframe, "loader": country_orders},
    ],
    key="table-selectbox-table",
)
