# headroom-charts

Live terminal dashboard for Headroom context-compression savings.

Reads `~/.headroom/savings_events.jsonl` and repaints once a second: tokens saved, cost
avoided, one bar per compression, and the latest events.

## Run it

From GitHub, no install step:

```bash
uvx --from git+https://github.com/shipschematic/headroom-charts headroom-charts
```

Or install it once and get a real binary on your `PATH`:

```bash
uv tool install --from git+https://github.com/shipschematic/headroom-charts headroom-charts
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

Three KPIs, a bar chart, and the latest events:

```
╭─ HEADROOM COMPRESSION DASHBOARD ─────────────────────────────────╮
╭─ 74,514          │ $0.2235          │ 20                         │
│  Tokens Saved    │ Cost Avoided     │ Compressions               │
│  (window)        │ (window)         │ (window)                   │
│  lifetime 112,580│ lifetime $0.3377 │ lifetime 37                │
╭─ Live Tokens Saved Per Call  last 20 of 37 · 10-27 23:02-10-28 01:27 ─╮
╭─ Latest Events ───────────────────────────────────────────────────────╮
```

Big numbers cover the last 20 events. The `lifetime` line sums the whole log. Cost
figures are list-price ceilings, so the real saving is likely lower.

## Data

Reads `ts`, `model`, `saved`, and `cost_usd` from each line of
`~/.headroom/savings_events.jsonl`. Bad lines are skipped.

## Development

```bash
uv run ruff check .
uv run mypy src
uv run pytest -q
```

## Docs

- [Behaviour specification](docs/SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)

## License

MIT
