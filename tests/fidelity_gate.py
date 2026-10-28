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

import datetime
import json
import pathlib

from rich.console import Console

from headroom_charts import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "golden" / "baselines.json"
DATA = ROOT / "tests" / "data"
ORIGINAL_COMMIT = "778c6ab"


class GateError(ValueError):
    """The recorded baseline cannot be trusted."""


def load_manifest(path: pathlib.Path = MANIFEST) -> dict:
    return json.loads(path.read_text())


def event_lines(
    count: int,
    start: str = "2026-10-27T22:55:00+00:00",
    step_minutes: int = 5,
    saved: int = 1000,
) -> str:
    """Synthetic events-log text, for shapes the checked-in fixtures do not cover."""
    first = datetime.datetime.fromisoformat(start)
    rows = [
        json.dumps(
            {
                "v": 2,
                "ts": (first + datetime.timedelta(minutes=step_minutes * i)).isoformat(),
                "before": 10000,
                "after": 10000 - saved,
                "saved": saved,
                "cost_usd": saved * 0.00001,
                "model": "beam",
                "client": "opencode",
                "source": "proxy",
                "pid": 4200,
                "saved_tool_schema": 0,
            }
        )
        for i in range(count)
    ]
    return "\n".join(rows) + "\n"


def render_frame(log_path: pathlib.Path) -> str:
    """generate_dashboard against one events log, at 100x30 truecolour."""
    console = Console(force_terminal=True, color_system="truecolor", width=100, height=30)
    return _render(console, log_path)


def render_text(log_path: pathlib.Path, width: int = 100, height: int = 30) -> str:
    """The same frame without colour or cursor codes, for reading what it says."""
    console = Console(force_terminal=False, no_color=True, width=width, height=height)
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


def _check_entry(entry: dict, manifest_path: pathlib.Path) -> None:
    name = entry["file"]
    path = manifest_path.parent / name
    if not path.is_file():
        raise GateError(f"baseline {name} does not exist at {path}")

    if entry.get("status") == "verbatim":
        if entry.get("captured_from") != ORIGINAL_COMMIT:
            raise GateError(f"verbatim baseline {name} must claim {ORIGINAL_COMMIT}")
        if "rendered_from" in entry:
            raise GateError(f"verbatim baseline {name} also claims rendered_from")
        return

    if "captured_from" in entry:
        raise GateError(
            f"baseline {name} claims captured_from {entry['captured_from']}, but a superseding "
            "frame was rendered by the current app.py and must record rendered_from instead"
        )
    if not (entry.get("authorized_by") and entry.get("date") and entry.get("rendered_from")):
        raise GateError(
            f"baseline {name} supersedes the verbatim frame but records no authorized_by decision"
        )


def _plots_full_window(fixture: str) -> bool:
    count = sum(1 for line in (DATA / fixture).read_text().splitlines() if line.strip())
    return count > app.MAX_BARS


def authorized_baselines(manifest_path: pathlib.Path = MANIFEST) -> list[dict]:
    manifest = load_manifest(manifest_path)
    recorded = {entry["file"]: entry for entry in manifest["baselines"]}

    verbatim_by_fixture: dict[str, str] = {}
    for entry in manifest["baselines"]:
        _check_entry(entry, manifest_path)
        if entry.get("status") == "verbatim":
            if entry["fixture"] in verbatim_by_fixture:
                raise GateError(
                    f"two verbatim frames for {entry['fixture']}: "
                    f"{verbatim_by_fixture[entry['fixture']]} and {entry['file']}"
                )
            verbatim_by_fixture[entry["fixture"]] = entry["file"]

    resolved: list[dict] = []
    for name in manifest["authorized"]:
        if name not in recorded:
            raise GateError(f"authorised baseline {name} is not recorded in {manifest_path}")
        resolved.append({**recorded[name], "path": manifest_path.parent / name})

    if not any(_plots_full_window(entry["fixture"]) for entry in resolved):
        raise GateError(
            "no authorised baseline plots a full window, so a change to MAX_BARS could not "
            f"be seen in any gated frame (need a log longer than {app.MAX_BARS} events)"
        )

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
