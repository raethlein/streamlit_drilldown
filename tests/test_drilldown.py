from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from streamlit_drilldown import drilldown

EXAMPLES = sorted(
    path
    for path in (Path(__file__).parent.parent / "examples").glob("*.py")
    if path.name != "sample_data.py"
)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_example_renders_first_level(example):
    at = AppTest.from_file(str(example), default_timeout=30).run()

    assert not at.exception


def _selectbox_app():
    import streamlit as st

    from streamlit_drilldown import drilldown, value

    def load_regions(element):
        element("Region", ["Europe", "Asia"], index=None)
        return value

    def load_countries(element, region):
        element(f"Country in {region}", ["A", "B"], index=None)
        return value

    def load_orders(element, region, country):
        st.write(f"orders of {region}/{country}")

    drilldown(
        [
            {"title": "Regions", "element": st.selectbox, "loader": load_regions},
            {"title": "Countries", "element": st.selectbox, "loader": load_countries},
            {"title": "Orders", "element": st.selectbox, "loader": load_orders},
        ],
        key="test",
    )


def test_drills_down_and_back():
    at = AppTest.from_function(_selectbox_app).run()
    assert at.selectbox[0].label == "Region"
    assert not at.button

    at.selectbox[0].select("Europe").run()
    assert at.selectbox[0].label == "Country in Europe"
    assert at.caption[0].value == "Europe"
    assert at.button[0].label == "Back"

    at.selectbox[0].select("B").run()
    assert at.markdown[-1].value == "orders of Europe/B"

    at.button[0].click().run()
    assert at.selectbox[0].label == "Country in Europe"
    assert at.selectbox[0].value is None

    at.button[0].click().run()
    assert at.selectbox[0].label == "Region"
    assert not at.button


def test_rejects_empty_levels():
    with pytest.raises(ValueError, match="at least one level"):
        drilldown([], key="x")


def test_rejects_level_without_loader():
    import streamlit as st

    with pytest.raises(ValueError, match="missing"):
        drilldown([{"element": st.dataframe}], key="x")  # type: ignore[typeddict-item]
