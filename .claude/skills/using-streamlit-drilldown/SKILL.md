---
name: using-streamlit-drilldown
description: Builds drilldown UIs in Streamlit apps with the streamlit-drilldown package, where a selection in a dataframe row, chart point, pill or selectbox opens the next level in the same place with a back button. Use when asked to add drill-down, master-detail or linked levels of elements to a Streamlit app, or when editing code that calls `drilldown(...)` from `streamlit_drilldown`.
---

# Using streamlit-drilldown

The README is the source of truth for the API and the concepts. Read [README.md](../../../README.md) first, and do not restate it in answers or code comments.

## Workflow

1. Decide the hierarchy: one level per step, top level first. Each level is an element (`st.dataframe`, `st.echarts_chart`, `st.pills`, `st.selectbox`, ...) and a loader.
2. Write one loader per level. Follow "Loaders" and "Resolvers" in the README: render through the `element` argument, take the earlier selections as positional arguments, and return a resolver (nothing for the last level).
3. Pick the resolver for each element from the helper table in the README. Write a one-line resolver for other elements.
4. Call `drilldown([...], key="<unique key>")` once per hierarchy.
5. Move heavy data access into `@st.cache_data` functions. See "Performance" in the README. Never decorate a loader itself.
6. Run the app and click through every level, including **Back**.

## Rules

- Never pass `key`, `on_select`, `on_change` or `on_click` in a loader's `element(...)` call. The drilldown supplies them.
- Give `st.selectbox` and similar widgets `index=None`, or they drill down on their own.
- Return `None` from a resolver while nothing is selected.
- Give every drilldown on a page its own `key`.
- Use `selectedMode` on the chart series for `st.echarts_chart` levels that must be selectable.

## Examples

Start from the closest file in [examples/](../../../examples/). The README table lists what each one shows. Reuse its structure, and keep each loader small.

## Checking the work

Run `uv run pytest`. Add a test with Streamlit's `AppTest` for new drilldowns, as in `tests/test_drilldown.py`.
