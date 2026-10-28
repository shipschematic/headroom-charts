"""Versioned behaviour baseline.

SPEC §6 used to say any render change must fail. That made the acknowledged
defects in the original unlandable. This gate replaces the blanket ban: the
verbatim frame stays the authorised baseline until a superseding baseline records
the decision that accepted a change.
"""

from __future__ import annotations

import contextlib
import json
import pathlib
from collections.abc import Iterator

from rich.console import Console

from headroom_charts import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "golden" / "baselines.json"
FIXTURE_LOG = str(ROOT / "tests" / "data" / "events.jsonl")


class GateError(ValueError):
    """The recorded baseline cannot be trusted."""


def load_manifest(path: pathlib.Path = MANIFEST) -> dict:
    return json.loads(path.read_text())


@contextlib.contextmanager
def _fixture_log() -> Iterator[None]:
    original = app.SAVINGS_FILE
    app.SAVINGS_FILE = FIXTURE_LOG
    try:
        yield
    finally:
        app.SAVINGS_FILE = original


def render_frame() -> str:
    """The shipped frame: generate_dashboard at 100x30 truecolour."""
    console = Console(force_terminal=True, color_system="truecolor", width=100, height=30)
    with _fixture_log(), console.capture() as capture:
        console.print(app.generate_dashboard())
    return capture.get()


def authorized_baseline(manifest_path: pathlib.Path = MANIFEST) -> dict:
    manifest = load_manifest(manifest_path)
    recorded = {entry["file"]: entry for entry in manifest["baselines"]}
    name = manifest["authorized"]

    if name not in recorded:
        raise GateError(f"authorised baseline {name} is not recorded in {manifest_path}")
    entry = recorded[name]

    has_decision = entry.get("authorized_by") and entry.get("date")
    if entry.get("status") != "verbatim" and not has_decision:
        raise GateError(
            f"baseline {name} supersedes the verbatim frame but records no authorized_by decision"
        )

    path = manifest_path.parent / name
    if not path.is_file():
        raise GateError(f"baseline {name} does not exist at {path}")

    return {**entry, "path": path}


def assert_frame_passes_gate() -> None:
    baseline = authorized_baseline()
    expected = baseline["path"].read_text()
    frame = render_frame()

    if frame != expected:
        raise AssertionError(
            f"frame does not match the authorised baseline {baseline['file']}, so "
            "no decision authorises this change. Capture the new frame as a "
            "superseding baseline in tests/golden/baselines.json first."
        )
