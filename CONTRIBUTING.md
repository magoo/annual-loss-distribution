# Contributing

Thank you for improving the Marimo annual-loss model. This project treats numerical
behavior as a public contract, so changes should be easy to review and reproduce.

## Development workflow

Start with the [local setup instructions](README.md#run-on-your-computer). To edit
and explore the Python notebook in [Marimo](https://marimo.io/), run:

```bash
uv run marimo edit app.py
```

1. Create a focused branch from the current `main` branch.
2. Install the locked environment with `uv sync --locked`.
3. Make a small, cohesive change. Keep UI code in `app.py` and reusable behavior in
   `annual_loss/`.
4. Add tests that demonstrate the intended behavior and relevant failure modes.
5. Run the complete local checks before committing:

   ```bash
   uv run ruff format --check .
   uv run ruff check .
   uv run pytest
   uv run marimo check --strict app.py
   ```

6. Open a pull request describing the user-visible effect, numerical implications,
   tests performed, and any follow-up work.

## Dependency changes

Use established, actively maintained libraries for probability, random sampling,
and numerical work. NumPy and SciPy are the default choices. Before adding a package,
confirm that the capability is not already available in the standard library or an
existing dependency.

Add dependencies with uv and commit both `pyproject.toml` and `uv.lock`:

```bash
uv add package-name
uv add --dev development-package-name
```

Keep dependency changes separate from unrelated feature work where practical. CI
installs with `uv sync --locked`, so an out-of-date lockfile will fail validation.
Use `uv lock` after manually changing dependency declarations, and commit `uv.lock`.

## Testing expectations

- Unit-test formulas, validation, interpolation, formatting, reporting, and workload
  guards directly.
- For stochastic behavior, use explicit fixed seeds and tolerance-based assertions
  over moments, quantiles, monotonicity, finiteness, and support.
- Cover distribution mode, linked scenario mode with paired per-row aggregation,
  and transitions into and out of scenario mode.
- Include zero-event years, heavy tails, invalid ordering, non-finite values, and
  maximum-workload boundaries where relevant.
- Verify notebook changes with Marimo's static checker and, for workflow changes, a
  local app smoke test.
- For UI, simulation, or deployment changes, build with
  `uv run python scripts/build_pages.py` and run `uv run pytest browser_tests`.
  Install Chromium and Firefox first with `uv run playwright install chromium firefox`.
  These tests exercise the browser runtime at the GitHub Pages subdirectory; native
  Python tests alone do not cover WebAssembly's 32-bit array indices or iframe behavior.

## GitHub Pages build and deployment

Build the interactive browser app and run its Chromium and Firefox acceptance tests:

```bash
uv sync --locked
uv run python scripts/build_pages.py
uv run playwright install chromium firefox
uv run pytest browser_tests
```

The tests serve the build at `/annual-loss-distribution/`, including its bundled
local Python package. On Linux, use `uv run playwright install --with-deps chromium firefox`
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

## Pull request checklist

- [ ] The change has a single clear purpose.
- [ ] Tests cover new behavior and regressions.
- [ ] Ruff, pytest, and Marimo checks pass.
- [ ] Numerical semantics and safety limits remain explicit.
- [ ] Documentation is updated where behavior or interfaces changed.
- [ ] `uv.lock` is current when dependencies changed.
- [ ] No secrets, local data, caches, or generated editor artifacts are included.

## Privacy review before publication

Keep Marimo's generated `__marimo__/` session output local. It can contain rendered
inputs and results, and is ignored along with virtual environments, caches, logs,
and `.env` configuration files. Never force-add these files. Keep confidential risk
scenarios, real incident data, and exported reports outside the repository; use only
sanitized examples in source, tests, and documentation. Any `.env.example` must
contain placeholders only because it is intentionally allowed in Git.

Before staging, inspect `git status --short --untracked-files=all` and `git diff`,
and read any new files you intend to include. Stage reviewed paths explicitly, then
inspect `git diff --cached --name-status` and `git diff --cached` before committing.
Ignore rules do not remove files that are already tracked or present in history.

Before publishing or pushing, scan both the working directory (including untracked
files) and Git history with a locally installed secret scanner. For example, with
TruffleHog:

```bash
trufflehog filesystem --no-verification --no-update .
trufflehog git --no-verification --no-update "file://$PWD"
```

These options disable credential verification and update checks. The directory scan
also examines ignored files, so review findings from installed dependencies and
generated output as well as project files. Resolve findings before publication and
ask the file's owner about ambiguous personal or confidential content. Do not paste
candidate secret values into issues, pull requests, or scan reports. A clean scan
does not replace reviewing the actual files and commit author information.

## Reporting issues

For modeling defects, include sanitized inputs, the seed, effective round count,
expected behavior, and observed behavior. Never attach confidential risk scenarios or
real incident data to a public issue.
