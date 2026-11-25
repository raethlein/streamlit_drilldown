"""Large data: filter the cached subset of the level above, not the full DataFrame.

`subset(path)` is cached per path, and a path's subset is built from the cached
subset of its parent path. So `region=Europe, country=Spain` filters the rows
that `region=Europe` already selected.

`st.cache_resource` hands out the stored DataFrame without copying it, which
matters for large subsets. Never modify the returned DataFrame, and bound the
cache with `max_entries` or `ttl`.

Run with: streamlit run examples/chained_subsets.py
"""

import sample_data

import pandas as pd
import streamlit as st
from streamlit_drilldown import drilldown, selected_row


@st.cache_resource(max_entries=200)
def subset(path: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    if not path:
        return sample_data.ORDERS
    *parent, (column, wanted) = path
    df = subset(tuple(parent))
    return df[df[column] == wanted]


def path_of(columns, selections):
    return tuple(zip(columns, selections))


def summary_loader(group, columns):
    def load(element, *selections):
        df = subset(path_of(columns, selections))
        summary = df.groupby(group, as_index=False)["revenue"].sum()
        element(summary, selection_mode="single-row", hide_index=True)
        return selected_row(summary, group)

    return load


def orders_table(element, region, country, product):
    path = path_of(["region", "country", "product"], [region, country, product])
    element(subset(path), hide_index=True)


st.title("Chained subsets")

drilldown(
    [
        {"title": "Regions", "element": st.dataframe, "loader": summary_loader("region", [])},
        {
            "title": "Countries",
            "element": st.dataframe,
            "loader": summary_loader("country", ["region"]),
        },
        {
            "title": "Products",
            "element": st.dataframe,
            "loader": summary_loader("product", ["region", "country"]),
        },
        {"title": "Orders", "element": st.dataframe, "loader": orders_table},
    ],
    key="chained",
)
