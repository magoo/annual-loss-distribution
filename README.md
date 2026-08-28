# Annual Loss Distribution for Marimo

A local, reactive application for turning security-risk estimates into annual-loss
distributions. This project ports the behavior of
[`magoo/annual-loss-distribution`](https://github.com/magoo/annual-loss-distribution)
from Svelte/JavaScript to Python and [Marimo](https://marimo.io/).

The application helps analysts:

- Model annual incident frequency and per-incident cost with lognormal, modified
  PERT, or Pareto distributions.
- Build named threat scenarios with independent frequency and cost methods.
- Combine frequency and cost through seeded Monte Carlo simulation.
- Aggregate multiple subject-matter-expert estimates in panel mode.
- Explore PDF/histogram and CDF views, modeled outcome ranges, and a copy-ready
  executive summary.

All modeling runs locally. The v1 application has no backend, authentication, or
persistent data store.

## Quick start

Install [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer, then run:

```bash
uv sync
uv run marimo edit app.py
```

The second command opens the notebook editor. To run the application in read-only
mode instead:

```bash
uv run marimo run app.py
```

## Development checks

Run the same checks used by CI before opening a pull request:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run marimo check --strict app.py
```

Use `uv lock` after intentionally changing dependencies, and commit `uv.lock` so
local and CI environments resolve the same versions.

## Architecture

- `app.py` is the Git-friendly Marimo notebook and contains presentation and
  interaction cells.
- `annual_loss/` contains typed, importable modeling code with no dependency on
  notebook state.
- `tests/` covers deterministic behavior, statistical properties, validation,
  workload limits, and reporting utilities.
- [`docs/source-review.md`](docs/source-review.md) records the upstream feature
  inventory, numerical semantics, review findings, and parity decisions.
- [`AGENTS.md`](AGENTS.md) defines repository-wide working agreements for coding
  agents and engineers.

Marimo's reactive dataflow is used for input previews and presentation. Expensive
Monte Carlo work is gated by an explicit Calculate/Recalculate action so routine UI
edits do not continually launch large simulations.

## Numerical trust and reproducibility

Production math uses NumPy and SciPy rather than custom probability or random-number
implementations. Every Monte Carlo result carries an explicit seed and effective
round count. Re-running the same validated inputs with the same seed must reproduce
the same result within the same locked environment.

Statistical parity with the upstream project means preserving its fitted
distributions and simulation semantics; it does not mean reproducing its JavaScript
PRNG sample stream byte-for-byte.

The output is a model derived from elicited assumptions. It is not a guarantee,
forecast, accounting opinion, or substitute for professional risk judgment.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Changes are expected to arrive through a
reviewable Git branch, include tests proportional to their risk, and pass all CI
checks.

## Attribution and license

This implementation is derived from the ISC-licensed
[`annual-loss-distribution`](https://github.com/magoo/annual-loss-distribution)
project by Ryan McGeehan. See [`LICENSE`](LICENSE).
