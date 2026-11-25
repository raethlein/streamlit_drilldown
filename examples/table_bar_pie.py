"""DataFrame -> bar chart -> pie chart.

Run with: streamlit run examples/table_bar_pie.py
"""

import sample_data

import streamlit as st
from streamlit_drilldown import drilldown, selected_point, selected_row


def regions_table(element):
    df = sample_data.revenue_by("region")
    element(df, selection_mode="single-row", hide_index=True)
    return selected_row(df, "region")


def countries_bar(element, region):
    df = sample_data.revenue_by("country", region=region)
    element(sample_data.bar_spec(df, "country"), height=320)
    return selected_point(df["country"].tolist())


def products_pie(element, region, country):
    # The last level returns nothing: there is nothing left to drill into.
    df = sample_data.revenue_by("product", region=region, country=country)
    element(sample_data.pie_spec(df, "product"), height=360)


st.title("Table → bar chart → pie chart")

drilldown(
    [
        {"title": "Revenue by region", "element": st.dataframe, "loader": regions_table},
        {"title": "Countries", "element": st.echarts_chart, "loader": countries_bar},
        {"title": "Product share", "element": st.echarts_chart, "loader": products_pie},
    ],
    key="table-bar-pie",
)
