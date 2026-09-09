# Repository instructions

These instructions apply to the entire repository. Keep changes reviewable,
reproducible, and safe for both engineers and coding agents.

## Project contract

- This is a Python 3.11+ Marimo application for security annual-loss modeling.
- Keep `app.py` focused on UI composition and reactive dataflow. Put reusable math,
  validation, simulation, formatting, and reporting logic in `annual_loss/`.
- The upstream behavior and approved parity decisions are documented in
  `docs/source-review.md`. Update that document when intentionally changing model
  semantics.
- V1 is local and in-memory. Do not add a backend, telemetry, authentication,
  persistence, or external data transmission without explicit approval.

## Setup and required checks

Use uv for dependency and command execution:

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run marimo check --strict app.py
```

Run the narrowest relevant test while iterating, then run the complete check set
before handing off a change. Do not commit caches, virtual environments, generated
coverage output, or editor state. Commit `uv.lock` whenever dependency resolution
changes.

## Numerical correctness rules

- Use `numpy.random.Generator` with an explicit seed for every stochastic path.
  Do not use module-global random state, Python's `random` module, or a custom PRNG.
- Use NumPy/SciPy primitives for sampling, distribution functions, quantiles, and
  other trusted numerical operations. New production dependencies require a clear
  justification and a lockfile update.
- Keep modeling functions deterministic for a given input and seed. Return or expose
  the seed and effective simulation round count with results.
- Validate finite, ordered, non-negative parameters before fitting or sampling. Fail
  clearly on unsafe workloads; do not silently truncate invalid inputs or simulated
  tails.
- Preserve annual-loss semantics: sample a yearly frequency, round it to a
  non-negative integer, independently sample one cost for each event, and sum those
  costs for that year.
- Preserve the documented workload ceilings and adaptive round behavior unless a
  reviewed change updates the specification, implementation, and tests together.
- Statistical tests must use fixed seeds and defensible tolerances. Do not assert
  exact equality for distribution moments or quantiles unless the operation is
  mathematically exact.

## Marimo conventions

- Prefer small cells with explicit inputs and outputs. Avoid hidden mutable state and
  callback-oriented control flow.
- Keep expensive simulations behind the Calculate/Recalculate action; previews may
  be reactive only when their cost is bounded.
- Do not define the same named variable in multiple cells. Keep imports near the
  beginning and allow Marimo's dependency graph to determine execution order.
- Make validation visible beside the relevant control and prevent calculation when
  inputs are incomplete, invalid, non-finite, or computationally unsafe.
- Keep notebook-specific code thin enough that core behavior can be tested without
  starting a Marimo server.

## Change control and review

- Inspect the working tree before editing and preserve unrelated user changes.
- Make focused commits and avoid drive-by refactors. Explain any numerical behavior
  change in the pull request.
- Add or update tests for every defect fix and behavior change. Update README or
  source-review documentation when interfaces, workflow, or assumptions change.
- Never weaken validation, safety limits, deterministic seeding, or test tolerances
  merely to make a check pass.

## Code review rules

- Flag unseeded randomness, custom probability math where SciPy provides a tested
  implementation, and any mismatch between displayed and simulated parameters.
- Flag reuse of a single cost draw across multiple incidents; event costs must be
  independent draws.
- Flag reactive paths that can start unbounded simulations during routine edits.
- Flag changes that describe a modeled outcome range as a parameter-estimation
  confidence interval.
