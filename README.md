# Annual Loss Distribution for Marimo

A reactive application for turning security-risk estimates into annual-loss
distributions, built with Python and [Marimo](https://marimo.io/).

**[Open Annual Loss Distribution](https://magoo.github.io/annual-loss-distribution/)**

This version replaces the original Svelte/JavaScript application. Its source remains
available in the repository history and the `legacy-svelte-2026-09-08` tag.

The application helps analysts:

- Work through three numbered, always-visible sections—Frequency, Cost, and
  Calculate—in one top-to-bottom page.
- Model annual incident frequency and per-incident cost with lognormal, modified
  PERT, or Pareto distributions.
- Add, edit, and remove named threat scenarios in one expanded list, with
  method-aware frequency and cost forms that show only the inputs each model uses.
- Use one linked scenario mode: every scenario row pairs its own frequency and cost
  assumptions, and yearly losses are summed across the scenario set.
- Combine frequency and cost through seeded Monte Carlo simulation.
- Add and delete subject-matter experts in expanded panel lists, aggregate their
  estimates, and inspect parameter-level panel analytics.
- Explore PDF/histogram and CDF views, modeled outcome ranges, and a copy-ready
  executive summary.

All modeling runs locally: in your browser on GitHub Pages, or on your computer
when running Python directly. The application has no backend, authentication, or
persistent data store. The public website distributes the application code and
serves its bundled Python runtime and packages; your entered estimates stay in the
browser session.

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

## GitHub Pages build and deployment

Build the interactive browser app and run its Chromium and Firefox acceptance tests:

```bash
uv sync --locked
uv run python scripts/build_pages.py
uv run playwright install chromium firefox
uv run pytest browser_tests
```

The tests serve the build at `/annual-loss-distribution/`, including its bundled
local Python package. On Linux, use `playwright install --with-deps chromium firefox`
to install the browsers' system dependencies as well.

To preview the generated app manually:

```bash
uv run python -m http.server --bind 127.0.0.1 --directory dist
```

Open the printed HTTP address; opening `dist/index.html` directly will not work.
First startup requires internet access and downloads the WebAssembly Python runtime
and numerical packages from the same Pages site, so it takes longer than subsequent
loads. No third-party CDN or package service is needed at runtime. Use a current
Chromium or Firefox browser. Source editing is disabled in the published app.

CI checks Python code, builds the app, and tests both browsers on pull requests.
Successful runs on `main` deploy the same tested artifact through GitHub Pages;
the CI workflow also supports manual redeployment. Generated `dist/` and Marimo
session files remain ignored. The build publishes the app, assets, reviewed Python
package, and checksum-verified browser dependencies, with no saved execution output.

After deployment, run the same acceptance tests against the live site:

```bash
PAGES_TEST_URL=https://magoo.github.io/annual-loss-distribution/ uv run pytest browser_tests
```

The local exporter and Python environment are locked by `uv.lock`. The browser
runtime is separately pinned in `scripts/browser-runtime.lock.json`: Pyodide
314.0.0 / Python 3.14, NumPy 2.4.3, SciPy 1.17.1, and Plotly 6.9.0. The build downloads
these files into an ignored cache, verifies every checksum, and includes their
licenses. Browser tests block all third-party requests and enforce the notebook's
declared dependency ranges. Repeatability is tested within each browser runtime;
exact numerical identity across browser and native Python versions is not promised.

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

Marimo's reactive dataflow is used for input previews and presentation. The three
workflow sections remain visible together so analysts can review or revise earlier
assumptions without switching views. Expensive Monte Carlo work is gated by an
explicit Calculate/Recalculate action so routine UI edits do not continually launch
large simulations.

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
[original application](https://github.com/magoo/annual-loss-distribution/tree/53c864df0c9b7a8ef866858c7c27e2d43a67b864)
by Ryan McGeehan. See [`LICENSE`](LICENSE).
