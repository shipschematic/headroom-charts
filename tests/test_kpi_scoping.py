"""Ticket #12: a window sum must not look like a lifetime sum that went backwards.

The KPIs are sums over the plotted window, so when a large event rolls off the left
edge every number on screen falls while the log only grew. These figures are hand-summed
from the fixture values, not recomputed by the code under test.

events_long.jsonl  25 events: 9000, 8000, 7000, 6000, 5000, 4000, then 19 x 1000
                   window (last 20) = 23,000   lifetime = 58,000
events.jsonl        6 events: 5000, 2500, 7300, 2000, 2000, 100  both sums = 18,900
"""

from __future__ import annotations

import pathlib

import fidelity_gate

ROOT = pathlib.Path(__file__).resolve().parents[1]
LONG_LOG = ROOT / "tests" / "data" / "events_long.jsonl"
SHORT_LOG = ROOT / "tests" / "data" / "events.jsonl"

# One more 500-token event: the 4000 at the head of the window rolls off.
ROLLED = (
    '{"v":2,"ts":"2026-10-27T22:55:00+00:00","before":10000,"after":9500,"saved":500,'
    '"cost_usd":0.005,"model":"beam","client":"opencode","source":"proxy","pid":4200,'
    '"saved_tool_schema":0}\n'
)


def test_window_and_lifetime_tokens_are_both_visible() -> None:
    frame = fidelity_gate.render_text(LONG_LOG)
    assert "23,000" in frame
    assert "lifetime 58,000" in frame


def test_every_kpi_is_labelled_as_a_window() -> None:
    frame = fidelity_gate.render_text(LONG_LOG)
    for label in ("Tokens Saved (window)", "Cost Avoided (window)", "Compressions (window)"):
        assert label in frame


def test_the_lifetime_anchor_survives_a_number_falling_out_of_the_window(
    tmp_path: pathlib.Path,
) -> None:
    log = tmp_path / "savings_events.jsonl"
    log.write_text(LONG_LOG.read_text() + ROLLED)

    before = fidelity_gate.render_text(LONG_LOG)
    after = fidelity_gate.render_text(log)

    assert "23,000" in before and "lifetime 58,000" in before
    assert "19,500" in after and "lifetime 58,500" in after


def test_a_log_shorter_than_the_window_anchors_at_the_same_total() -> None:
    frame = fidelity_gate.render_text(SHORT_LOG)
    assert "18,900" in frame
    assert "lifetime 18,900" in frame
