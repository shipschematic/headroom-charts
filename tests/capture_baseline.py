"""Record a superseding behaviour baseline.

    uv run python tests/capture_baseline.py "#11"

Renders every gated fixture with the current code, writes the frames beside the
authorised ones as `<name>.vN.txt`, and re-points `baselines.json` at them with the
issue and date that authorise the change. Superseded frames are kept, so the verbatim
behaviour stays attributable. Refuses to run without an issue reference: a frame
change with no decision behind it is exactly what the gate is for.
"""

from __future__ import annotations

import datetime
import json
import sys

import fidelity_gate as gate


def next_filename(current: str) -> str:
    stem = current.removesuffix(".txt")
    existing = [int(p.stem.rsplit(".v", 1)[1]) for p in gate.MANIFEST.parent.glob(f"{stem}.v*.txt")]
    return f"{stem}.v{max(existing, default=1) + 1}.txt"


def main(issue_ref: str, today: str | None = None) -> int:
    if not issue_ref.startswith("#"):
        raise SystemExit('usage: capture_baseline.py <issue-ref> — e.g. "#11"')
    today = today or datetime.date.today().isoformat()

    manifest = gate.load_manifest()
    captured: list[str] = []

    for name in manifest["authorized"]:
        entry = next(b for b in manifest["baselines"] if b["file"] == name)
        frame = gate.render_frame(gate.DATA / entry["fixture"])
        new_name = next_filename(name)
        (gate.MANIFEST.parent / new_name).write_text(frame)
        manifest["baselines"].append(
            {
                **{k: v for k, v in entry.items() if k != "note"},
                "file": new_name,
                "status": "superseding",
                "supersedes": name,
                "authorized_by": issue_ref,
                "date": today,
                "note": f"Current render at 100x30 truecolour, authorised by {issue_ref}.",
            }
        )
        captured.append(new_name)

    manifest["authorized"] = captured
    gate.MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"authorised baselines -> {captured}  (authorized_by {issue_ref})")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
