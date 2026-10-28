# headroom-charts

Live terminal dashboard for [Headroom](https://github.com/shipblueprint/headroom)
context-compression savings.

Reads `~/.headroom/savings_events.jsonl` and redraws once a second: tokens saved, cost
avoided, a bar chart per compression, and the latest events.

## Run it

From GitHub, no install step:

```bash
uvx --from git+https://github.com/shipblueprint/headroom-charts headroom-charts
```

Or install it once and get a real binary on your `PATH`:

```bash
uv tool install --from git+https://github.com/shipblueprint/headroom-charts headroom-charts
headroom-charts
```

Once it is on PyPI, `uvx headroom-charts` works too — it is not published yet.
Requires Python 3.10+.

Takes over the alternate screen, like `htop`. Ctrl-C restores your terminal.

## Running from a local checkout

`uvx --from <path>` does **not** run your working tree. It builds a wheel from that
directory and runs the copy in uv's cache, so edits to the source stay invisible:

```bash
# wrong for development — serves the last cached build
uvx --from /path/to/headroom-charts headroom-charts

# right: runs the source directly
uv run --directory /path/to/headroom-charts headroom-charts

# or keep using uvx but force a rebuild
uvx --refresh --from /path/to/headroom-charts headroom-charts
```

## What you see

Three KPIs and a chart. Each KPI carries **two scopes**, because the chart plots only a
rolling window and that difference is otherwise invisible:

```
╭─ HEADROOM COMPRESSION DASHBOARD ─────────────────────────────────╮
╭─ 74,514          │ $0.2235          │ 20                         │
│  Tokens Saved    │ Cost Avoided     │ Compressions               │
│  (window)        │ (window)         │ (window)                   │
│  lifetime 112,580│ lifetime $0.3377 │ lifetime 37                │
╭─ Live Tokens Saved Per Call  last 20 of 37 · 10-27 23:02-10-28 01:27 ─╮
╭─ Latest Events ───────────────────────────────────────────────────────╮
```

The **big number is the window** — the last 20 events, which is what the bars plot. When
a large event rolls off the left edge, it can fall while the log only grew. The
`lifetime` line under it sums the whole file, so it is the figure that reconciles with
`headroom`'s own summary. The chart title states which events are in the window; a
window crossing midnight names the day on each end.

Cost figures are **list-price ceilings**, mirroring `headroom`'s caveat: some events are
priced at flat list price, so the real saving is likely lower.

## Data

Reads `ts`, `model`, `saved`, and `cost_usd` from each line of
`~/.headroom/savings_events.jsonl`. Bad lines are skipped.

## Development

```bash
uv run ruff check .          # app.py is deliberately exempt, see docs/ARCHITECTURE.md
uv run mypy src
uv run pytest -q
```

`src/headroom_charts/app.py` is vendored from the original single-file script and its
render is guarded by a byte-level golden test. Changing what the dashboard draws
requires a recorded supersession — see SPEC §6.

Design and parity policy: [`docs/SPEC.md`](docs/SPEC.md),
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## License

MIT
