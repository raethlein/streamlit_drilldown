"""Sample sales data and helpers shared by the examples."""

import time

import numpy as np
import pandas as pd

import streamlit as st

COUNTRIES = {
    "Europe": ["Germany", "France", "Spain"],
    "Americas": ["USA", "Canada", "Brazil"],
    "Asia": ["Japan", "India"],
}

_rng = np.random.default_rng(42)
ORDERS = pd.DataFrame(
    [
        {
            "region": region,
            "country": country,
            "product": product,
            "month": month.strftime("%Y-%m"),
            "revenue": int(_rng.integers(100, 1000)),
        }
        for region, countries in COUNTRIES.items()
        for country in countries
        for product in ["Widget", "Gadget", "Gizmo"]
        for month in pd.date_range("2025-01-01", periods=6, freq="MS")
    ]
)


def _filter(**filters: str) -> pd.DataFrame:
    df = ORDERS
    for column, wanted in filters.items():
        df = df[df[column] == wanted]
    return df


# The data access is cached, not the loaders. A loader renders widgets and
# returns a function, which `st.cache_data` can neither run nor store.
@st.cache_data
def revenue_by(group: str, **filters: str) -> pd.DataFrame:
    """Total revenue per `group`, for the orders that match `filters`."""
    time.sleep(0.3)  # Stands in for a slow query.
    return _filter(**filters).groupby(group, as_index=False)["revenue"].sum()


@st.cache_data
def orders(**filters: str) -> pd.DataFrame:
    """The orders that match `filters`."""
    time.sleep(0.3)
    return _filter(**filters)


def bar_spec(df: pd.DataFrame, category: str) -> dict:
    """An ECharts bar chart of revenue per `category`, with selectable bars."""
    return {
        "tooltip": {},
        "xAxis": {"type": "category", "data": df[category].tolist()},
        "yAxis": {},
        "series": [
            {"type": "bar", "data": df["revenue"].tolist(), "selectedMode": "single"}
        ],
    }


def pie_spec(df: pd.DataFrame, category: str) -> dict:
    """An ECharts donut chart of revenue per `category`."""
    return {
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": [
                    {"name": name, "value": revenue}
                    for name, revenue in zip(df[category], df["revenue"])
                ],
            }
        ],
    }


def line_spec(df: pd.DataFrame, category: str) -> dict:
    """An ECharts line chart of revenue per `category`."""
    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": df[category].tolist()},
        "yAxis": {},
        "series": [{"type": "line", "data": df["revenue"].tolist()}],
    }
