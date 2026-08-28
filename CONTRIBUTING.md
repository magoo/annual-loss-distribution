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
- Cover distribution-only, scenario-only, and both hybrid frequency/cost paths.
- Include zero-event years, heavy tails, invalid ordering, non-finite values, and
  maximum-workload boundaries where relevant.
- Verify notebook changes with Marimo's static checker and, for workflow changes, a
  local app smoke test.

## Pull request checklist

- [ ] The change has a single clear purpose.
- [ ] Tests cover new behavior and regressions.
- [ ] Ruff, pytest, and Marimo checks pass.
- [ ] Numerical semantics and safety limits remain explicit.
- [ ] Documentation is updated where behavior or interfaces changed.
- [ ] `uv.lock` is current when dependencies changed.
- [ ] No secrets, local data, caches, or generated editor artifacts are included.

## Reporting issues

For modeling defects, include sanitized inputs, the seed, effective round count,
expected behavior, and observed behavior. Never attach confidential risk scenarios or
real incident data to a public issue.
