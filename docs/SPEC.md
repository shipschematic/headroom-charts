# headroom-charts — Behaviour Specification

Status: v1, describing shipped behaviour · Last updated: 2026-10-28

**Source of truth is the code, not this document.** [`src/headroom_charts/app.py`](../src/headroom_charts/app.py)
is the original `headroom-charts.py` verbatim; this file describes what that code
does so a packaging change can be checked against it. It is not a wish list.

## 1. Purpose

Watch a context-compression proxy's token savings while it runs, in one terminal
screen, without `tail -f` and reading raw JSON. A viewer only — it never writes the
events file.

## 2. Data contract

`~/.headroom/savings_events.jsonl` — append-only JSON Lines, one event per line,
schema version `v: 2`. A real line:

```json
{"v":2,"ts":"2026-10-27T21:06:59.766090+00:00","before":65046,"after":62184,
 "saved":2862,"cost_usd":0.008586,"model":"beam","client":"opencode",
 "source":"proxy","pid":27451,"saved_tool_schema":0}
```

| Field | Type | Used | Notes |
|---|---|---|---|
| `v` | int | no | always `2` in observed data |
| `ts` | string | **yes** | ISO-8601 with offset; sliced as `[11:16]` for `HH:MM` and `[:19]` for the table |
| `before` | int | no | prompt tokens pre-compression |
| `after` | int | no | prompt tokens post-compression |
| `saved` | int | **yes** | bar height and the token KPI |
| `cost_usd` | float | **yes** | cost KPI |
| `model` | string | **yes** | table column |
| `client`, `source`, `pid`, `saved_tool_schema` | — | no | present in the log, not displayed |

Tolerated input:

- File absent → `get_events()` returns `[]` and the chart prints `Waiting for data...`.
- Malformed line → `json.JSONDecodeError` is caught and the line skipped.
- Missing field → `.get()` default of `0`, `0.0` or `"unknown"`.
- The whole file is parsed; the last `MAX_BARS = 20` events are plotted and summed as
  the window, and the full list feeds the lifetime anchor and the window provenance.
  The earlier last-100-lines cap changed nothing about the window — 20 is already
  inside 100 — and under-reported the total, so it went with #11. The per-repaint
  whole-file read is still open as #9.

## 3. Interface

Four zones in a `rich` `Layout`, repainted once per second on the alternate screen
(`Live(screen=True, refresh_per_second=1)`).

| Zone | Rows | Contents |
|---|---|---|
| header | 3 | `HEADROOM COMPRESSION DASHBOARD`, ivory-on-maroon, RUST border |
| kpi | 5 | window `Tokens Saved` · `Cost Avoided` · `Compressions`, each with a `lifetime` anchor |
| chart | ratio 1 | `Live Tokens Saved Per Call`, HARVEST border, bars over an axis |
| footer | 8 | `Latest Events` table, last 5 as `Time │ Model │ Saved`, newest first |

Chart, exactly as implemented:

- Up to `MAX_BARS = 20` events, oldest on the left.
- `CHART_HEIGHT = 10` rows, scaled by the largest `saved` in the window (`or 1` so a
  zero window cannot divide by zero).
- Bar height is `int((val / max_val) * 10)` — truncated, so a low-but-nonzero value
  can render as no bar.
- A filled cell is `██ `, an empty cell is three spaces.
- Y-axis gutter is `{value:>6} ┤ `; baseline is `       └` + `───` per bar.
- X labels are minutes; above 15 events only every third bar is labelled.
- The chart title carries **window provenance** — `last 20 of 25 · 20:35-22:48` when
  the log is longer than the window, `6 events · 09:00-09:05` when it is not, and
  `no events yet` with no log. Added by #11; it is the only place a reader learns
  which events the numbers cover.

Each KPI is two numbers. The top line is the **window** sum — `saved`, `cost_usd` and
event count over the same ≤20 events the chart plots. Under it sits a `lifetime`
anchor summed over the whole log. The original's `(Recent)` label is gone because the
scope is now spelled out on both lines. The anchor exists for a specific failure of the
window sum: when a large event rolls off the left edge, every top-line figure *falls*
while the log has only grown, which reads as data loss unless something on screen
moves the other way.

### Reconciling with `headroom`'s own summary

`headroom` prints lifetime totals; the top KPI line prints the window. On a real
37-event log the two read as:

```
headroom     saved 112,580 / 1,062,752 tokens   $0.3377   37 calls
dashboard    saved  74,514  (window)            $0.2235   20 compressions (window)
             saved 112,580  (lifetime)          $0.3377   37 (lifetime)
```

The lifetime line is now the same figure `headroom` prints, so the two screens
reconcile without a spreadsheet. The window line omits the 17 oldest events, worth
38,066 tokens and $0.1142. `headroom` divides by total prompt tokens, which this
dashboard never reads (`before` is unconsumed — see #6), so the 10.6% ratio still has
no equivalent on screen.

Palette — 24-bit hex, from the original HTML mockup:

| Name | Hex | Used for |
|---|---|---|
| `HARVEST` | `#BB9457` | bars, KPI numerals, chart border |
| `ESPRESSO` | `#432818` | panel `style` |
| `RUST` | `#99582A` | borders, axes, table columns |
| `MAROON` | `#6F1D1B` | header background, model column |
| `IVORY` | `#EFE3D2` | text and labels |

`rich` maps these onto whatever colour system the terminal reports; verified to draw
on `TERM=dumb`, `vt100` and `xterm-256color`.

## 4. Invocation

```
headroom-charts
```

No options, matching the original script. Exits `0`, including on `Ctrl-C`, which the
loop catches and passes.

## 5. Non-goals

- **Any change to rendering, layout sizes, geometry or palette without a recorded
  decision.** Packaging was a distribution change, not a redesign, and the verbatim
  frame is still the baseline. A deliberate change is now landable — see §6.
- Reading any file other than the one path above.
- Writing, rotating or backfilling the events log.
- Cost estimation — `cost_usd` is displayed as given.
- Network access, telemetry, config files, mouse input, panes, history zoom.

## 6. Fidelity acceptance

The gate for every change to what the dashboard draws:

1. `python headroom-charts.py` and the installed `headroom-charts` command emit
   **identical bytes** for the same terminal size and the same events file.
2. Both exit `0` on `Ctrl-C`.
3. A rendered frame at 100×30 against each gated events log equals the **authorised
   baseline** named in [`tests/golden/baselines.json`](../tests/golden/baselines.json).
   Two logs are gated: the 6-event one, and a 25-event one whose window is full — a
   log shorter than the window draws identically at any `MAX_BARS` at or above its
   length, so the short frame alone cannot see a window change. The `verbatim` entries
   were captured from the original script at `778c6ab`; `#11` superseded both.
4. Changing a constant in §3 — a hex, `MAX_BARS`, `CHART_HEIGHT`, a zone size — fails
   that golden test, because no decision authorises it.
5. A change a human has accepted lands by **supersession**: run
   `uv run python tests/capture_baseline.py "#<issue>"`, which renders the current
   frame for each gated log, writes it as `frame_<...>.vN.txt`, and records
   `authorized_by` and `date`. The superseded frame stays in the repo, so the verbatim
   behaviour remains attributable.

An entry that supersedes the verbatim baseline without naming a decision is rejected
by the gate rather than trusted, and a change with no new baseline still fails rule 4.
The gate itself is [`tests/fidelity_gate.py`](../tests/fidelity_gate.py); it exists
because rules 3–4 as first written made the known defects in §5 of
docs/ARCHITECTURE.md permanently unlandable.

Known defects in the original are tracked separately; see docs/ARCHITECTURE.md §5.
