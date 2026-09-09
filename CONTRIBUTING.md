# Contributing

Thank you for improving the Marimo annual-loss model. This project treats numerical
behavior as a public contract, so changes should be easy to review and reproduce.

## Development workflow

1. Create a focused branch from the current `main` branch.
2. Install the locked environment with `uv sync`.
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
