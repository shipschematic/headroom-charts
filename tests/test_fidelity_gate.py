"""The fidelity gate: a render change may land only with a recorded decision."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile

import fidelity_gate
import pytest
from rich.console import Console

from headroom_charts import app

GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"
SHORT = "frame_100x30.txt"
LONG = "frame_long_100x30.txt"


def render_with_original_script(fixture: str) -> str:
    """Draw with the original single-file script, taken out of git history."""
    source = subprocess.run(
        ["git", "show", f"{fidelity_gate.ORIGINAL_COMMIT}:headroom-charts.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(source)
        name = handle.name
    try:
        spec = importlib.util.spec_from_file_location("original_script", name)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.SAVINGS_FILE = str(fidelity_gate.DATA / fixture)
        console = Console(force_terminal=True, color_system="truecolor", width=100, height=30)
        with console.capture() as capture:
            console.print(module.generate_dashboard())
        return capture.get()
    finally:
        os.unlink(name)


def write_manifest(tmp_path: pathlib.Path, manifest: dict) -> pathlib.Path:
    for entry in manifest["baselines"]:
        (tmp_path / entry["file"]).write_text("x")
    path = tmp_path / "baselines.json"
    path.write_text(json.dumps(manifest))
    return path


def test_frame_matches_every_authorised_baseline() -> None:
    fidelity_gate.assert_frame_passes_gate()


def test_verbatim_baselines_are_recorded_and_still_on_disk() -> None:
    for name in (SHORT, LONG):
        entry = next(b for b in fidelity_gate.load_manifest()["baselines"] if b["file"] == name)
        assert entry["status"] == "verbatim"
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


def test_supersession_numbering_steps_one_version(tmp_path: pathlib.Path) -> None:
    """A superseded name must not stack: frame.v2.txt becomes frame.v3.txt, not v2.v2."""
    capture = importlib.import_module("capture_baseline")
    assert capture.next_filename("frame_100x30.txt", tmp_path) == "frame_100x30.v2.txt"
    (tmp_path / "frame_100x30.v2.txt").write_text("x")
    assert capture.next_filename("frame_100x30.v2.txt", tmp_path) == "frame_100x30.v3.txt"


def test_superseding_frames_never_claim_the_original_script() -> None:
    """A vN frame was rendered by the edited app.py; attributing it to 778c6ab is a lie."""
    for entry in fidelity_gate.load_manifest()["baselines"]:
        if entry["status"] == "verbatim":
            assert entry["captured_from"] == fidelity_gate.ORIGINAL_COMMIT
            assert "rendered_from" not in entry
        else:
            assert "captured_from" not in entry
            assert entry["rendered_from"]


def test_verbatim_frames_really_are_the_original_scripts_frames() -> None:
    """Re-derive them from the commit they claim, instead of trusting the manifest."""
    repo = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
    if repo.returncode:
        pytest.skip("not a git checkout")
    for entry in fidelity_gate.load_manifest()["baselines"]:
        if entry["status"] != "verbatim":
            continue
        expected = render_with_original_script(entry["fixture"])
        assert (GOLDEN / entry["file"]).read_text() == expected


def test_the_gate_refuses_a_baseline_set_that_cannot_see_the_window(tmp_path: pathlib.Path) -> None:
    """Six events against MAX_BARS=20 draws the same at any window size."""
    manifest = {
        "authorized": [SHORT],
        "baselines": [
            {
                "file": SHORT,
                "fixture": "events.jsonl",
                "status": "verbatim",
                "captured_from": "778c6ab",
            },
        ],
    }
    (tmp_path / SHORT).write_text("x")
    with pytest.raises(fidelity_gate.GateError, match="full window"):
        fidelity_gate.authorized_baselines(write_manifest(tmp_path, manifest))

def test_the_gate_refuses_two_verbatim_frames_for_one_fixture(tmp_path: pathlib.Path) -> None:
    """One verbatim frame per fixture is the whole point of calling it verbatim."""
    manifest = {
        "authorized": ["frame_second.txt"],
        "baselines": [
            {
                "file": SHORT,
                "fixture": "events.jsonl",
                "status": "verbatim",
                "captured_from": "778c6ab",
            },
            {
                "file": "frame_second.txt",
                "fixture": "events.jsonl",
                "status": "verbatim",
                "captured_from": "778c6ab",
            },
        ],
    }
    (tmp_path / "frame_second.txt").write_text("x")
    with pytest.raises(fidelity_gate.GateError, match="verbatim"):
        fidelity_gate.authorized_baselines(write_manifest(tmp_path, manifest))


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
    path = write_manifest(tmp_path, manifest)
    (tmp_path / "frame_100x30.v9.txt").unlink()
    with pytest.raises(fidelity_gate.GateError, match="does not exist"):
        fidelity_gate.authorized_baselines(path)
