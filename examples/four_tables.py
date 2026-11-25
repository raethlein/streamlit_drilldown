"""Four levels of tables, built from one loader factory.

Levels that only differ in the column they group by can share a loader.

Run with: streamlit run examples/four_tables.py
"""

import sample_data

import streamlit as st
from streamlit_drilldown import drilldown, selected_row


def table_loader(group, filter_columns):
    """A loader that groups by `group`, filtered by the selections above."""

    def load(element, *selections):
        filters = dict(zip(filter_columns, selections))
        df = sample_data.revenue_by(group, **filters)
        element(df, selection_mode="single-row", hide_index=True)
        return selected_row(df, group)

    return load


def orders_table(element, region, country, product):
    element(
        sample_data.orders(region=region, country=country, product=product),
        hide_index=True,
    )


st.title("Four tables")

drilldown(
    [
        {"title": "Regions", "element": st.dataframe, "loader": table_loader("region", [])},
        {
            "title": "Countries",
            "element": st.dataframe,
            "loader": table_loader("country", ["region"]),
        },
        {
            "title": "Products",
            "element": st.dataframe,
            "loader": table_loader("product", ["region", "country"]),
        },
        {"title": "Orders", "element": st.dataframe, "loader": orders_table},
    ],
    key="four-tables",
)
