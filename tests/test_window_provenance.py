"""Ticket #11: the window states which events it is summarising.

The dashboard sums a rolling window, so its totals are lower than `headroom`'s own
summary by design. Before this, nothing on screen said so, and the difference read as
a bug. Verified through the rendered frame only.
"""

from __future__ import annotations

import pathlib

import fidelity_gate

ROOT = pathlib.Path(__file__).resolve().parents[1]
LONG_LOG = ROOT / "tests" / "data" / "events_long.jsonl"
SHORT_LOG = ROOT / "tests" / "data" / "events.jsonl"
MISSING_LOG = pathlib.Path("/tmp/not-an-events-log.jsonl")


def test_a_truncated_window_says_it_is_the_last_of_more() -> None:
    assert "last 20 of 25" in fidelity_gate.render_text(LONG_LOG)


def test_the_covered_time_span_is_readable() -> None:
    assert "20:35-22:48" in fidelity_gate.render_text(LONG_LOG)


def test_a_short_log_is_not_claimed_as_a_full_window() -> None:
    frame = fidelity_gate.render_text(SHORT_LOG)
    assert "20 of 6" not in frame
    assert "6 events" in frame


def test_an_absent_log_says_there_are_no_events() -> None:
    frame = fidelity_gate.render_text(MISSING_LOG)
    assert "no events yet" in frame
    assert "0 events" not in frame
