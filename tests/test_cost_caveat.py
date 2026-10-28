"""Ticket #13: the dollar figure needs the caveat `headroom` puts on it.

`headroom` prints "Some events are priced at flat list price ... The real saving is
likely LOWER" under its cost summary. The dashboard printed a bare figure with no such
hedge. No pricing is computed here — the stored `cost_usd` is still what is shown.
"""

from __future__ import annotations

import pathlib

import fidelity_gate

ROOT = pathlib.Path(__file__).resolve().parents[1]
LONG_LOG = ROOT / "tests" / "data" / "events_long.jsonl"


def test_the_caveat_names_the_limit() -> None:
    frame = fidelity_gate.render_text(LONG_LOG)
    assert "list-price ceiling" in frame
    assert "likely lower" in frame


def test_the_recorded_sum_is_still_the_number_shown() -> None:
    """The caveat marks the figure, it does not adjust it: $0.23 is the stored total."""
    frame = fidelity_gate.render_text(LONG_LOG)
    assert "$0.2300" in frame
    assert "lifetime $0.5800" in frame


def test_the_caveat_does_not_push_the_kpi_row_apart() -> None:
    """#8 already clips the footer; this must not add a second clip on the KPI row."""
    for width in (100, 80):
        frame = fidelity_gate.render_text(LONG_LOG, width=width)
        assert max(len(line) for line in frame.splitlines()) <= width
        for text in ("23,000", "$0.2300", "lifetime 58,000", "lifetime $0.5800", "lifetime 25"):
            assert text in frame, f"{text!r} lost at {width} cols"
