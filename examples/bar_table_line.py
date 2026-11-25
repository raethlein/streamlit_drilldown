"""Bar chart -> DataFrame -> line chart.

Run with: streamlit run examples/bar_table_line.py
"""

import sample_data

import streamlit as st
from streamlit_drilldown import drilldown, selected_point, selected_row


def regions_bar(element):
    df = sample_data.revenue_by("region")
    element(sample_data.bar_spec(df, "region"), height=300)
    return selected_point(df["region"].tolist())


def countries_table(element, region):
    df = sample_data.revenue_by("country", region=region)
    element(df, selection_mode="single-row", hide_index=True)
    return selected_row(df, "country")


def monthly_line(element, region, country):
    df = sample_data.revenue_by("month", region=region, country=country)
    element(sample_data.line_spec(df, "month"), height=320)


st.title("Bar chart → table → line chart")

drilldown(
    [
        {"title": "Revenue by region", "element": st.echarts_chart, "loader": regions_bar},
        {"title": "Countries", "element": st.dataframe, "loader": countries_table},
        {"title": "Monthly revenue", "element": st.echarts_chart, "loader": monthly_line},
    ],
    key="bar-table-line",
)
