"""Ticket #11: the window states which events it is summarising.

The dashboard sums a rolling window, so its totals are lower than `headroom`'s own
summary by design. Before this, nothing on screen said so, and the difference read as
a bug. Verified through the rendered frame only.
"""

from __future__ import annotations

import pathlib

import pytest
from rich.console import Console

from headroom_charts import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
LONG_LOG = ROOT / "tests" / "data" / "events_long.jsonl"
SHORT_LOG = ROOT / "tests" / "data" / "events.jsonl"


def render_plain(log_path: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(app, "SAVINGS_FILE", log_path)
    console = Console(force_terminal=False, no_color=True, width=100, height=30)
    with console.capture() as capture:
        console.print(app.generate_dashboard())
    return capture.get()


def test_a_truncated_window_says_it_is_the_last_of_more(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = render_plain(str(LONG_LOG), monkeypatch)
    assert "last 20 of 25" in frame


def test_the_covered_time_span_is_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = render_plain(str(LONG_LOG), monkeypatch)
    assert "20:35-22:48" in frame


def test_a_short_log_is_not_claimed_as_a_full_window(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = render_plain(str(SHORT_LOG), monkeypatch)
    assert "20 of 6" not in frame
    assert "6 events" in frame


def test_an_absent_log_says_there_are_no_events(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = render_plain("/tmp/not-an-events-log.jsonl", monkeypatch)
    assert "no events yet" in frame
    assert "0 events" not in frame
