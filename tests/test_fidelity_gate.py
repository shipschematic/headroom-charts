"""The fidelity gate: a render change may land only with a recorded decision."""

from __future__ import annotations

import json
import pathlib

import fidelity_gate
import pytest

from headroom_charts import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERBATIM_BASELINE = "frame_100x30.txt"


def write_manifest(tmp_path: pathlib.Path, manifest: dict) -> pathlib.Path:
    path = tmp_path / "baselines.json"
    path.write_text(json.dumps(manifest))
    return path


def test_gate_passes_the_current_render_against_the_authorized_baseline() -> None:
    fidelity_gate.assert_frame_passes_gate()


def test_verbatim_baseline_is_recorded_and_still_on_disk() -> None:
    manifest = fidelity_gate.load_manifest()
    entry = next(b for b in manifest["baselines"] if b["file"] == VERBATIM_BASELINE)
    assert entry["status"] == "verbatim"
    assert entry["captured_from"] == "778c6ab"
    assert (ROOT / "tests" / "golden" / VERBATIM_BASELINE).is_file()
    # Until a decision supersedes it, the verbatim frame is the gate.
    assert manifest["authorized"] == VERBATIM_BASELINE


def test_unauthorised_palette_change_fails_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "HARVEST", "#000000")
    with pytest.raises(AssertionError, match="no decision authorises"):
        fidelity_gate.assert_frame_passes_gate()


def test_supersession_without_a_decision_is_rejected(tmp_path: pathlib.Path) -> None:
    manifest = {
        "authorized": "frame_100x30.v2.txt",
        "baselines": [
            {"file": VERBATIM_BASELINE, "status": "verbatim", "captured_from": "778c6ab"},
            {"file": "frame_100x30.v2.txt", "status": "superseding"},
        ],
    }
    (tmp_path / "frame_100x30.v2.txt").write_text("x")
    with pytest.raises(fidelity_gate.GateError, match="authorized_by"):
        fidelity_gate.authorized_baseline(write_manifest(tmp_path, manifest))


def test_supersession_naming_a_missing_frame_is_rejected(tmp_path: pathlib.Path) -> None:
    manifest = {
        "authorized": "frame_100x30.v2.txt",
        "baselines": [
            {"file": VERBATIM_BASELINE, "status": "verbatim", "captured_from": "778c6ab"},
            {
                "file": "frame_100x30.v2.txt",
                "status": "superseding",
                "authorized_by": "#11",
                "date": "2026-10-28",
            },
        ],
    }
    with pytest.raises(fidelity_gate.GateError, match="does not exist"):
        fidelity_gate.authorized_baseline(write_manifest(tmp_path, manifest))
