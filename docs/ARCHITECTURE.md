# headroom-charts — Packaging Architecture

Status: v1 · Last updated: 2026-10-28

## 1. The packaging decision

**PyPI, not npm.** The tool is ~150 lines of Python on one dependency, `rich`.
Shipping it through npm would mean rewriting every panel, table and bar in `ink` or
`blessed` — discarding working code, and still leaving the npm user without a Python
runtime. The dependency graph is one library deep; PyPI is its native home.

| Route | Install UX | Cost | Verdict |
|---|---|---|---|
| **PyPI** + `pipx`/`uvx` | `uvx headroom-charts` | near zero | **Taken.** Isolated env, global command, no damage to system Python |
| Standalone binary per OS/arch (PyInstaller) | one file from a GitHub Release | CI matrix, ~30MB artifacts, no auto-update | Deferred to issue #7; only worth it if users genuinely lack Python |
| npm wrapping a wheel | `npm i -g` | a shim that solves nothing | Rejected |
| Homebrew tap / AUR | `brew install` | a formula to maintain per release | Optional later |

A binary is a second artifact over the same source, not an alternative to the
package — so the package comes first either way.

`headroom-charts` and `headroom-tui` were unclaimed on PyPI as of 2026-10-28;
`headroom` itself is taken, so the distribution name needs a suffix.

## 2. Layout

```
headroom-charts/
├── headroom-charts.py            # thin shim: from headroom_charts.app import run
├── pyproject.toml
├── src/headroom_charts/
│   ├── __init__.py               # __version__
│   ├── app.py                    # THE ORIGINAL SCRIPT — verbatim until superseded
│   ├── cli.py                    # main() -> app.run()
│   └── __main__.py               # python -m headroom_charts
└── tests/
    ├── data/events.jsonl         # 6-event fixture: below the window
    ├── data/events_long.jsonl    # 25-event fixture: window full, so its size is visible
    ├── golden/baselines.json     # which frame is authorised, and by which issue
    ├── golden/frame_*.txt        # captured from the original script at 778c6ab
    ├── golden/frame_*.v2.txt     # superseded forward by #11
    ├── golden/frame_*.v3.txt     # superseded forward by #12
    ├── fidelity_gate.py          # resolves the authorised baseline, compares frames
    ├── capture_baseline.py       # records a superseding baseline against an issue
    ├── test_fidelity_gate.py     # the gate itself, including that it bites
    ├── test_kpi_scoping.py       # window sums and lifetime anchors, separately labelled
    ├── test_parity.py            # palette, constants, entry points, live loop
    └── test_window_provenance.py # the screen says which events it sums
```

Four files of substance in `src/`, and `app.py` is the only one that contains program logic.

## 3. Parity policy

The job was distribution, not redesign. Three rules keep that true:

**One implementation.** `app.py` holds the original code, and every entry point —
the root script, the `headroom-charts` console command, and `python -m
headroom_charts` — routes to the same `app.run`. There is no second copy to drift.
`test_console_script_and_root_script_share_one_implementation` asserts the three
resolve to the identical function object.

**Byte-level golden.** [`tests/golden/frame_100x30.txt`](../tests/golden/frame_100x30.txt)
was captured by running the *original* [`headroom-charts.py` at `778c6ab`](https://github.com/shipblueprint/headroom-charts/blob/778c6ab/headroom-charts.py)
against the fixture log at 100×30 truecolour. `app.py`'s render must equal it exactly.
Verified to bite: setting `CHART_HEIGHT = 8`, or changing one palette hex, fails it.

**No autoformatting the renderer.** `app.py` is excluded from ruff lint and format,
and from mypy, in `pyproject.toml`. The original has long lines and an unused
`deque` import; rewriting those is a change to the file we promise is verbatim, and
formatting is how behaviour changes sneak in. Style debt is quarantined to one
commented exemption rather than spread through edits.

**Supersession, once a decision exists.** Those three rules made the frame frozen,
which was right while packaging was the only job and wrong afterwards: it left the
acknowledged defects in §5 with no way to land, because any fix fails the golden test
by construction. [`tests/fidelity_gate.py`](../tests/fidelity_gate.py) now resolves the
baseline from [`tests/golden/baselines.json`](../tests/golden/baselines.json), and a
change to the drawing is accepted by recording a superseding frame with
`authorized_by` and `date`. Absent that record, the verbatim frame is still the gate
and an unauthorised hex or size change still fails. The promise moves from "this never
changes" to "this only changes by decision".

Confirmed in a pty against an identical events file at 100×30: the two entry points
emitted **28,891 bytes each, byte-for-byte equal**, and both exited `0`.

## 4. pyproject.toml

`uv_build` backend — no setuptools, no `setup.py`, no duplicated version.

```toml
[project]
name = "headroom-charts"
version = "0.1.0"
requires-python = ">=3.10"
license = "MIT"
dependencies = ["rich>=13.0"]

[project.scripts]
headroom-charts = "headroom_charts.cli:main"
```

`[project.scripts]` is the line that turns the wheel into a command, and the reason
`pipx install` gives you a working `headroom-charts` binary.

## 5. Defects in the original

Found while packaging and left unfixed at the time, because the requirement was that
the packaged command match the script. That reason expired with #10: rendering now has
a decision path, so these stay open as ordinary issues rather than as frozen
behaviour. None of them is fixed below; the one gap that was not on this list — the
window never said which events it summed — is now closed by #11.

1. **The events table always clips.** The footer is allocated 8 rows but 5 data rows
   plus header and separator need 10, so **3 of 5 events are ever shown** — measured
   at both 24 and 30 rows tall, so it is not a short-terminal edge case. Issue #8.
2. **The x-axis can be pushed off-screen.** At 24 rows the chart's baseline and minute
   labels are clipped away entirely (`axis drawn = False`), leaving bars with no time
   reference. Issue #8.
3. **Whole-file read every second.** `f.readlines()[-100:]` loads the entire log into
   memory to keep the last 100 lines, once per repaint. Correct, but cost grows with
   file size, and `100` is unrelated to `MAX_BARS = 20`. Issue #9.
4. **Low savings render as no bar at all.** `int((val / max_val) * 10)` truncates, so
   any event under 5% of the window peak disappears. Issue #9.
5. **Nothing is configurable.** Path, `MAX_BARS`, `CHART_HEIGHT` and the 1s interval
   are module constants; the command takes no arguments. Issue #9.
6. **Minute-only labels across an hour.** A real window crossing 21:06 to 01:02
   rendered as `23 02 08 14 21 55 44` — correct, and unreadable. Issue #4.

## 6. Release flow

```
push main → CI: ruff, mypy, pytest (parity), uv build, twine check
tag v*    → CI: uv publish to PyPI + attach sdist/wheel to the GitHub Release
```

PyPI credentials should be trusted publishing (OIDC), scoped to this project — not a
long-lived token in repo secrets. Publishing is issue #2 and needs a human: PyPI
releases are effectively immutable, so a botched `0.1.0` can only be skipped over.
