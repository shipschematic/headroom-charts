"""The fidelity gate: a render change may land only with a recorded decision."""

from __future__ import annotations

import json
import pathlib

import fidelity_gate
import pytest

from headroom_charts import app

GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"
SHORT = "frame_100x30.txt"
LONG = "frame_long_100x30.txt"


def write_manifest(tmp_path: pathlib.Path, manifest: dict) -> pathlib.Path:
    (tmp_path / LONG).write_text("x")
    path = tmp_path / "baselines.json"
    path.write_text(json.dumps(manifest))
    return path


def test_frame_matches_every_authorised_baseline() -> None:
    fidelity_gate.assert_frame_passes_gate()


def test_verbatim_baselines_are_recorded_and_still_on_disk() -> None:
    for name in (SHORT, LONG):
        entry = next(b for b in fidelity_gate.load_manifest()["baselines"] if b["file"] == name)
        assert entry["status"] == "verbatim"
        assert entry["captured_from"] == "778c6ab"
        assert (GOLDEN / name).is_file()


def test_unauthorised_palette_change_fails_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "HARVEST", "#000000")
    with pytest.raises(AssertionError, match="no decision authorises"):
        fidelity_gate.assert_frame_passes_gate()


def test_unauthorised_window_change_fails_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a log longer than the window can show a window change, hence the 25-event frame."""
    monkeypatch.setattr(app, "MAX_BARS", 8)
    with pytest.raises(AssertionError, match="no decision authorises"):
        fidelity_gate.assert_frame_passes_gate()


def test_supersession_without_a_decision_is_rejected(tmp_path: pathlib.Path) -> None:
    manifest = {
        "authorized": [LONG],
        "baselines": [
            {"file": LONG, "fixture": "events_long.jsonl", "status": "superseding"},
        ],
    }
    with pytest.raises(fidelity_gate.GateError, match="authorized_by"):
        fidelity_gate.authorized_baselines(write_manifest(tmp_path, manifest))


def test_supersession_naming_a_missing_frame_is_rejected(tmp_path: pathlib.Path) -> None:
    manifest = {
        "authorized": ["frame_100x30.v9.txt"],
        "baselines": [
            {
                "file": "frame_100x30.v9.txt",
                "fixture": "events.jsonl",
                "status": "superseding",
                "authorized_by": "#11",
                "date": "2026-10-28",
            },
        ],
    }
    with pytest.raises(fidelity_gate.GateError, match="does not exist"):
        fidelity_gate.authorized_baselines(write_manifest(tmp_path, manifest))
