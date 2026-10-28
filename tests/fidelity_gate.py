"""Versioned behaviour baseline.

SPEC §6 used to say any render change must fail. That made the acknowledged
defects in the original unlandable. This gate replaces the blanket ban: the
verbatim frames stay the authorised baseline until a superseding baseline records
the decision that accepted a change.

Two fixtures are gated. The 6-event one pins the general frame; the 25-event one
is what makes the window size visible, because a log shorter than the window
draws identically at any MAX_BARS at or above its length.
"""

from __future__ import annotations

import json
import pathlib

from rich.console import Console

from headroom_charts import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "golden" / "baselines.json"
DATA = ROOT / "tests" / "data"


class GateError(ValueError):
    """The recorded baseline cannot be trusted."""


def load_manifest(path: pathlib.Path = MANIFEST) -> dict:
    return json.loads(path.read_text())


def render_frame(log_path: pathlib.Path) -> str:
    """generate_dashboard against one events log, at 100x30 truecolour."""
    console = Console(force_terminal=True, color_system="truecolor", width=100, height=30)
    return _render(console, log_path)


def render_text(log_path: pathlib.Path, width: int = 100) -> str:
    """The same frame without colour or cursor codes, for reading what it says."""
    console = Console(force_terminal=False, no_color=True, width=width, height=30)
    return _render(console, log_path)


def _render(console: Console, log_path: pathlib.Path) -> str:
    original = app.SAVINGS_FILE
    app.SAVINGS_FILE = str(log_path)
    try:
        with console.capture() as capture:
            console.print(app.generate_dashboard())
    finally:
        app.SAVINGS_FILE = original
    return capture.get()


def authorized_baselines(manifest_path: pathlib.Path = MANIFEST) -> list[dict]:
    manifest = load_manifest(manifest_path)
    recorded = {entry["file"]: entry for entry in manifest["baselines"]}
    resolved: list[dict] = []

    for name in manifest["authorized"]:
        if name not in recorded:
            raise GateError(f"authorised baseline {name} is not recorded in {manifest_path}")

        entry = recorded[name]
        has_decision = entry.get("authorized_by") and entry.get("date")
        if entry.get("status") != "verbatim" and not has_decision:
            raise GateError(
                f"baseline {name} supersedes the verbatim frame but records no "
                "authorized_by decision"
            )

        path = manifest_path.parent / name
        if not path.is_file():
            raise GateError(f"baseline {name} does not exist at {path}")

        resolved.append({**entry, "path": path})

    return resolved


def assert_frame_passes_gate() -> None:
    for baseline in authorized_baselines():
        frame = render_frame(DATA / baseline["fixture"])
        if frame != baseline["path"].read_text():
            raise AssertionError(
                f"frame for {baseline['fixture']} does not match the authorised baseline "
                f"{baseline['file']}, so no decision authorises this change. Capture the new "
                "frame as a superseding baseline in tests/golden/baselines.json first."
            )
