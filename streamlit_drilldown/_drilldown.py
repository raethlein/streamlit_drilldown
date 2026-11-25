"""Implementation of the drilldown. See the README for usage."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import Any, NotRequired, TypedDict

import streamlit as st

# Turns the value of a level's element into the selection for the next level,
# or None if nothing usable is selected.
Resolver = Callable[[Any], Any]

# `loader(element, *selections)`: renders the level through `element` and
# returns a resolver for the next level (nothing for the last level).
Loader = Callable[..., Resolver | None]

_CALLBACK_PARAMETERS = ("on_select", "on_change", "on_click")


class Level(TypedDict):
    """One level of the hierarchy."""

    element: Callable[..., Any]
    loader: Loader
    title: NotRequired[str]


def selected_row(df: Any, column: str) -> Resolver:
    """Resolver for `st.dataframe`: the value in `column` of the selected row."""

    def resolve(event: Any) -> Any:
        rows = event.selection.rows
        return df.iloc[rows[0]][column] if rows else None

    return resolve


def selected_point(names: Sequence[Any]) -> Resolver:
    """Resolver for `st.echarts_chart`: the name of the selected data point.

    `names` are the point names in the order of the chart's data.
    """

    def resolve(event: Any) -> Any:
        selected = event.selection.selected
        if not selected or not selected[0]["data_indices"]:
            return None
        return names[selected[0]["data_indices"][0]]

    return resolve


def value(selected: Any) -> Any:
    """Resolver for widgets whose value is the selection, such as `st.pills`."""
    return selected


def _callback_parameter(element: Callable[..., Any]) -> str | None:
    """The name of the element's callback parameter, if it has one."""
    try:
        parameters = inspect.signature(element).parameters
    except (TypeError, ValueError):
        return None
    return next((name for name in _CALLBACK_PARAMETERS if name in parameters), None)


class _State:
    """The selections made so far, kept in session state."""

    def __init__(self, key: str) -> None:
        self._key = f"_drilldown_{key}"
        if self._key not in st.session_state:
            st.session_state[self._key] = {"selections": [], "nonce": 0}

    @property
    def _data(self) -> dict[str, Any]:
        return st.session_state[self._key]

    @property
    def selections(self) -> list[Any]:
        return self._data["selections"]

    @property
    def nonce(self) -> int:
        return self._data["nonce"]

    def drill(self, selection: Any) -> None:
        self._data["selections"] = [*self.selections, selection]
        self._data["nonce"] += 1

    def back(self) -> None:
        self._data["selections"] = self.selections[:-1]
        self._data["nonce"] += 1


def _validate(levels: Sequence[Level]) -> None:
    if not levels:
        raise ValueError("`levels` must have at least one level.")
    for index, level in enumerate(levels):
        missing = {"element", "loader"} - set(level)
        if missing:
            raise ValueError(f"Level {index} is missing {sorted(missing)}.")
        unknown = set(level) - {"element", "loader", "title"}
        if unknown:
            raise ValueError(f"Level {index} has unknown keys: {sorted(unknown)}.")


def drilldown(levels: Sequence[Level], *, key: str) -> None:
    """Show one level at a time, where a selection in a level opens the next.

    Only the fragment around the drilldown reruns when the user drills down or
    goes back. A back button and a breadcrumb of the selections are built in.

    Parameters
    ----------
    levels:
        The hierarchy, top level first. Each level is a dict with

        - ``element``: any Streamlit command that accepts ``key``, such as
          ``st.dataframe``, ``st.echarts_chart``, ``st.selectbox`` or
          ``st.pills``.
        - ``loader``: a function ``loader(element, *selections)``.
          ``selections`` are the values chosen in the levels above. The loader
          calls ``element(...)`` to render the level and returns a resolver
          ``value -> selection``, where ``value`` is what the element returns.
          The resolver returns ``None`` while nothing is selected. The last
          level's loader returns nothing. Widgets that always have a value,
          such as ``st.selectbox``, need ``index=None`` so they start without a
          choice.
        - ``title`` (optional): shown above the level.
    key:
        A unique key for this drilldown.
    """
    _validate(levels)

    @st.fragment(key=key)
    def _drilldown() -> None:
        state = _State(key)
        selections = state.selections
        index = len(selections)
        level = levels[index]
        is_last = index == len(levels) - 1

        # A new key per navigation step gives each level a fresh selection.
        widget_key = f"{key}-L{index}-{state.nonce}"

        callback_parameter = None if is_last else _callback_parameter(level["element"])
        resolver_box: dict[str, Resolver | None] = {"resolver": None}
        rendered: dict[str, Any] = {}

        def resolve(element_value: Any) -> None:
            resolver = resolver_box["resolver"]
            selection = None if resolver is None else resolver(element_value)
            if selection is not None:
                state.drill(selection)

        def on_selection() -> None:
            # Runs before the fragment reruns, with the value that Streamlit
            # keeps in session state under the widget's key.
            resolve(st.session_state[widget_key])

        def element(*args: Any, **kwargs: Any) -> Any:
            if callback_parameter is not None:
                kwargs[callback_parameter] = on_selection
            rendered["value"] = level["element"](*args, key=widget_key, **kwargs)
            return rendered["value"]

        with st.container(horizontal=True, vertical_alignment="center"):
            if selections:
                st.button(
                    "Back",
                    icon=":material/arrow_back:",
                    type="tertiary",
                    key=f"{key}-back-{state.nonce}",
                    on_click=state.back,
                )
            if level.get("title"):
                st.markdown(f"**{level['title']}**")
            if selections:
                st.caption(" › ".join(str(selection) for selection in selections))

        resolver_box["resolver"] = level["loader"](element, *selections)

        # An element without a callback parameter is resolved after rendering.
        if not is_last and callback_parameter is None:
            resolve(rendered.get("value"))
            if state.selections != selections:
                st.rerun(scope="fragment")

    _drilldown()
