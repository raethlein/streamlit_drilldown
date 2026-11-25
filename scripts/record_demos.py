"""Record one video per example into docs/, for the README.

Needs the dev dependencies and a Chromium for Playwright:

    uv sync
    uv run playwright install chromium
    uv run python scripts/record_demos.py            # all examples
    uv run python scripts/record_demos.py table_bar_pie

Every example is started in its own Streamlit server and driven with
Playwright, which records the page as a WebM video. Playwright does not draw
the mouse pointer, so a small overlay shows it and ripples on every click. The
recording is then trimmed to the loaded app and converted to an MP4 and to an
animated WebP. A README on GitHub shows the WebP inline, as it only plays videos
that were uploaded through its web editor.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

import av
from playwright.sync_api import Page, sync_playwright

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
VIEWPORT = {"width": 760, "height": 500}
VIEWPORTS = {"dashboard_app": {"width": 1000, "height": 1040}}
HEADER_HEIGHT = 35  # Header row of st.dataframe.
ROW_HEIGHT = 35
FPS = 25

# A pointer that follows the mouse, and a ring that expands on every click.
POINTER_OVERLAY = """
window.addEventListener('DOMContentLoaded', () => {
  const style = document.createElement('style');
  style.textContent = `
    #demo-pointer { position: fixed; z-index: 2147483647; pointer-events: none;
      width: 22px; height: 22px; left: -50px; top: -50px; }
    .demo-ripple { position: fixed; z-index: 2147483646; pointer-events: none;
      width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%;
      border: 3px solid #ff4b4b; animation: demo-ripple 0.6s ease-out forwards; }
    @keyframes demo-ripple { to { transform: scale(3.2); opacity: 0; } }`;
  document.head.append(style);
  const pointer = document.createElement('div');
  pointer.id = 'demo-pointer';
  pointer.innerHTML = '<svg viewBox="0 0 22 22" width="22" height="22">' +
    '<path d="M2 1 L2 17 L6.5 13 L9.5 20 L12.5 18.7 L9.6 12 L15.5 12 Z" ' +
    'fill="#111" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  document.body.append(pointer);
  document.addEventListener('mousemove', (e) => {
    pointer.style.left = e.clientX - 2 + 'px';
    pointer.style.top = e.clientY - 1 + 'px';
  }, true);
  document.addEventListener('mousedown', (e) => {
    const ripple = document.createElement('div');
    ripple.className = 'demo-ripple';
    ripple.style.left = e.clientX + 'px';
    ripple.style.top = e.clientY + 'px';
    document.body.append(ripple);
    setTimeout(() => ripple.remove(), 700);
  }, true);
});
"""


def settle(page: Page) -> None:
    """Wait for the rerun to finish and the chart animations to play."""
    page.wait_for_timeout(300)
    page.wait_for_function(
        "!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=10_000
    )
    page.wait_for_timeout(1500)


def to_mp4(source: Path, target: Path) -> None:
    """Convert `source` to H.264, dropping the blank frames before the app shows."""
    with av.open(str(source)) as video_in, av.open(
        str(target), "w", options={"movflags": "faststart"}
    ) as video_out:
        stream_in = video_in.streams.video[0]
        stream_out = video_out.add_stream("libx264", rate=FPS)
        stream_out.width, stream_out.height = stream_in.width, stream_in.height
        stream_out.pix_fmt = "yuv420p"
        stream_out.options = {"crf": "20"}
        start: float | None = None
        last = -1
        for frame in video_in.decode(video=0):
            if start is None:
                if frame.to_ndarray(format="gray").std() < 2:  # Still blank.
                    continue
                start = float(frame.pts * stream_in.time_base)
            pts = round((float(frame.pts * stream_in.time_base) - start) * FPS)
            if pts <= last:
                continue
            last = pts
            frame.pts = pts
            frame.time_base = Fraction(1, FPS)
            video_out.mux(stream_out.encode(frame))
        video_out.mux(stream_out.encode())


def to_webp(source: Path, target: Path) -> None:
    """Convert the MP4 `source` to an animated WebP."""
    with av.open(str(source)) as video:
        frames = [frame.to_image() for frame in video.decode(video=0)]
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=1000 // FPS,
        loop=0,
        quality=70,
    )


def box_of(page: Page, selector: str) -> dict[str, float]:
    box = page.locator(selector).first.bounding_box()
    assert box is not None, f"{selector} is not visible"
    return box


def click_at(page: Page, x: float, y: float) -> None:
    """Glide the pointer to (x, y), click, and wait for the app to settle."""
    page.mouse.move(x, y, steps=30)
    page.wait_for_timeout(500)
    page.mouse.click(x, y)
    settle(page)
    page.wait_for_timeout(600)


def click_element(page: Page, selector: str) -> None:
    box = box_of(page, selector)
    click_at(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def click_row(page: Page, row: int) -> None:
    """Click the selection checkbox of a row in the visible st.dataframe."""
    box = box_of(page, '[data-testid="stDataFrame"]')
    click_at(
        page,
        box["x"] + 17,
        box["y"] + HEADER_HEIGHT + ROW_HEIGHT * row + ROW_HEIGHT / 2,
    )


def click_bar(page: Page, index: int, count: int) -> None:
    """Click bar `index` of `count` in the visible bar chart."""
    box = box_of(page, '[data-testid="stEChartsChart"]')
    plot_left = box["x"] + box["width"] * 0.1
    plot_right = box["x"] + box["width"] * 0.9
    x = plot_left + (plot_right - plot_left) * (index + 0.5) / count
    click_at(page, x, box["y"] + box["height"] - 75)  # Just above the x axis.


def click_pill(page: Page, name: str) -> None:
    box = page.get_by_role("radio", name=name, exact=True).bounding_box()
    assert box is not None
    click_at(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def choose_option(page: Page, name: str) -> None:
    click_element(page, '[data-testid="stSelectbox"]')
    option = page.get_by_role("option", name=name, exact=True).bounding_box()
    assert option is not None
    click_at(
        page, option["x"] + option["width"] / 2, option["y"] + option["height"] / 2
    )


def click_back(page: Page) -> None:
    box = page.get_by_role("button", name="Back").bounding_box()
    assert box is not None
    click_at(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def table_bar_pie(page: Page) -> None:
    click_row(page, 0)  # Americas
    click_bar(page, 0, 3)  # Brazil
    click_back(page)


def bar_table_line(page: Page) -> None:
    click_bar(page, 1, 3)  # Asia
    click_row(page, 0)
    click_back(page)


def pills_bar_table(page: Page) -> None:
    click_pill(page, "Asia")
    click_bar(page, 0, 2)  # India
    click_back(page)


def table_selectbox_table(page: Page) -> None:
    click_row(page, 2)  # Europe
    choose_option(page, "France")
    click_back(page)


def dashboard_app(page: Page) -> None:
    click_row(page, 2)  # Europe
    click_bar(page, 0, 3)  # France
    click_back(page)
    click_back(page)
    # A filter reruns the whole script: the counters change and the slow chart reloads.
    choose_option(page, "Gadget")
    page.wait_for_timeout(1500)


def four_tables(page: Page) -> None:
    for _ in range(3):
        click_row(page, 0)
    click_back(page)


EXAMPLES: dict[str, Callable[[Page], None]] = {
    "dashboard_app": dashboard_app,
    "table_bar_pie": table_bar_pie,
    "bar_table_line": bar_table_line,
    "pills_bar_table": pills_bar_table,
    "table_selectbox_table": table_selectbox_table,
    "four_tables": four_tables,
    "chained_subsets": four_tables,  # The same clicks, on a different implementation.
}


@contextmanager
def serve(example: str, port: int) -> Iterator[str]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "examples" / f"{example}.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{url}/_stcore/health", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError(f"{example} did not start")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


def record(example: str, port: int) -> None:
    DOCS.mkdir(exist_ok=True)
    with (
        serve(example, port) as url,
        sync_playwright() as playwright,
        tempfile.TemporaryDirectory() as video_dir,
    ):
        viewport = VIEWPORTS.get(example, VIEWPORT)
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport=viewport,
            record_video_dir=video_dir,
            record_video_size=viewport,
        )
        context.add_init_script(POINTER_OVERLAY)
        page = context.new_page()
        page.goto(f"{url}/?embed=true")
        page.wait_for_selector('[data-testid="stMain"]')
        settle(page)
        page.mouse.move(viewport["width"] - 40, viewport["height"] - 40)
        page.wait_for_timeout(800)
        EXAMPLES[example](page)
        page.wait_for_timeout(1500)
        context.close()  # Finishes the video file.
        recording = Path(page.video.path())
        browser.close()
        path = DOCS / f"{example}.mp4"
        to_mp4(recording, path)
        to_webp(path, path.with_suffix(".webp"))
    webp = path.with_suffix(".webp")
    print(f"{path.name}: {path.stat().st_size // 1024} KB, {webp.name}: {webp.stat().st_size // 1024} KB")


def main() -> None:
    names = sys.argv[1:] or list(EXAMPLES)
    for offset, name in enumerate(names):
        record(name, 8700 + offset)


if __name__ == "__main__":
    main()
