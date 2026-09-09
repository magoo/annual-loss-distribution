# Upstream source review and Marimo parity specification

## Review baseline

This review covers
[`magoo/annual-loss-distribution`](https://github.com/magoo/annual-loss-distribution)
at commit
[`53c864df0c9b7a8ef866858c7c27e2d43a67b864`](https://github.com/magoo/annual-loss-distribution/tree/53c864df0c9b7a8ef866858c7c27e2d43a67b864),
the tip of `main` reviewed on 2026-08-28.

The upstream application is a client-side Svelte 5/Vite application. Its purpose is
to make security-risk elicitation approachable: an analyst describes how often
incidents occur and how much each incident costs, then receives an annual-loss curve
and an executive-readable summary.

## Feature inventory

The user workflow presents three numbered sections in one top-to-bottom page:
Frequency, Cost, and Calculate. All three remain visible so an analyst can review or
revise earlier assumptions while progressing through the sequence.

Frequency and Cost each support:

- Lognormal and Pareto models fitted from P50 and P95 estimates.
- Modified PERT models fitted from minimum, most likely, and maximum estimates.
- Distribution-specific guidance, defaults, inline validation, PDF/CDF previews, and
  an adjustable chart focus percentile.
- Panel mode with named experts. It becomes active with two panelists, models the
  arithmetic mean of each elicited parameter, and reports average, minimum, maximum,
  and sample standard deviation by field.

Scenario mode provides a shared list of named threats. Each scenario has:

- A frequency method: `1 in N years` odds, lognormal, PERT, or Pareto.
- A cost distribution: lognormal, PERT, or Pareto.
- Independent parameters for frequency and cost, add/edit/remove behavior, and an
  optional mini distribution preview.
- Ten seeded default threats, including Product Exploit, Malicious Insider, DDoS,
  Supply Chain, credential theft, social engineering, exposed services, and
  ransomware.

Calculate combines the reviewed inputs and provides:

- A distribution/histogram view and empirical CDF view in Plotly.
- Loss-specific hover text with percentile and exceedance probability.
- A focus control for heavy-tailed ranges and an annotation for zero-loss mass.
- A configurable central modeled outcome range from 50% through 95%, including
  lower bound, median, upper bound, and copyable prose.
- A copy-ready executive summary covering simulation setup, source estimates,
  distributions or scenarios, and modeled ranges for frequency, cost, and loss.

The application is entirely local to the browser and has no backend or persistence.

## Numerical behavior to preserve

### Distribution fitting and display

- Lognormal: `mu = ln(P50)` and
  `sigma = (ln(P95) - mu) / Phi^-1(0.95)`, with the upstream approximation
  `Phi^-1(0.95) = 1.6449`.
- Modified PERT: a beta distribution scaled to `[min, max]`, using lambda 4,
  `alpha = 1 + 4(mode - min)/(max - min)`, and
  `beta = 1 + 4(max - mode)/(max - min)`.
- Pareto: `shape = ln(10) / ln(P95/P50)` and
  `scale = P50 / 2^(1/shape)`.
- Analytic curves contain 500 points. Lognormal covers P0.1 to P99.9 on a
  log-spaced x-axis; PERT covers its finite support linearly; Pareto starts at its
  scale and extends to its P99.9 value on a log-spaced x-axis.
- Empirical CDFs preserve zero mass and the simulated maximum while using a compact,
  mostly log-spaced grid through the central 99.8% of positive outcomes.
- Percentiles shown in modeled ranges are linearly interpolated from displayed CDF
  arrays. The range is predictive model output, not a confidence interval for fitted
  parameters.

### Distribution-mode annual loss

For each simulated year, the engine samples one frequency value, rounds it to the
nearest integer, clamps it to zero or greater, independently samples one cost for
every resulting event, and sums those costs. Frequency and cost may use different
supported distribution families.

The desired run size is 100,000 years. It adapts downward using the estimated
frequency work rate and a target of 750,000 event-cost draws, but never below 1,000
years. The engine rejects a count above 100,000 events in one year or a run above
1,500,000 total event-cost draws.

### Scenario annual loss

Scenario simulations target 10,000 years and use the same lower round bound and work
ceilings when costs are required.

- Each scenario independently produces its annual count, and every event uses that
  same row's cost distribution.
- Losses from every scenario row are summed to produce each simulated year's total.
- `1 in N years` is a Bernoulli trial with annual probability `1/N`; distribution
  frequencies are rounded to non-negative integer counts.

The upstream simulation module contains hybrid code paths, but the Svelte application
has one global scenario-mode flag and does not expose those combinations. This port
keeps that coherent user-facing model: scenario frequency and scenario cost always
activate together, with no hybrid simulation API.

### Validation and reproducibility

- P50 and P95 must be finite and positive, with P95 greater than P50.
- PERT inputs must be finite and satisfy `0 <= min < mode < max`.
- Odds must be finite and at least 1.
- Frequency inputs are rejected before simulation when their high estimate or
  expected workload violates the safety limits. Pareto frequency models with an
  infinite theoretical mean use P95 only as a planning proxy; hard draw limits still
  apply during simulation.
- The upstream uses a custom Mulberry32 PRNG with hard-coded seed 12345 for
  distribution annual loss and 54321 for scenario simulation.

## Code-review findings and migration decisions

1. Preserve statistical semantics, formulas, defaults, validation, zero-loss mass,
   and workload limits. Exact JavaScript samples are not a compatibility target.
2. Replace jStat and Mulberry32 with SciPy distribution functions and an explicit
   `numpy.random.Generator`. Make the seed and effective round count visible in every
   simulation result.
3. Keep Direct and Panel choices independent, but link Scenario mode across Frequency
   and Cost. Selecting Threat Scenarios in either section activates both; leaving it
   restores the other section's last Direct or Panel choice. Pair each scenario row's
   frequency and cost models and sum their annual losses. Do not expose ambiguous
   hybrid combinations.
4. Keep panel aggregation intentionally simple: arithmetic means of elicited fields
   drive the fitted model, while analytics use sample standard deviation. This is
   parameter aggregation, not mathematical pooling of expert distributions.
5. Gate full Monte Carlo work behind an explicit Calculate/Recalculate action. The
   upstream derives chart data reactively, which is natural in Svelte but can repeat
   expensive work as inputs change.
6. Keep reporting language precise: say `modeled outcome range`, not statistical
   `confidence interval`. Include the actual seed and effective rounds in result and
   report metadata.
7. Keep all inputs in memory for v1. Persistence, authentication, and telemetry
   remain outside the implementation. The approved Pages migration adds an
   interactive WebAssembly export: Python and the existing modeling package run
   in the visitor's browser, with no simulation backend or uploaded estimates.
   Runtime and package downloads require internet access. Preserve the same model,
   workload limits, and explicit Calculate/Recalculate boundary in this environment.

## GitHub Pages migration

The Python application replaces the Svelte application in the existing public
repository. The `legacy-svelte-2026-09-08` tag preserves the old app for rollback;
both implementations' commit histories remain reachable. The separately created
private `security-org-planning-annual-loss` repository remains a backup.

The build uses Marimo's WebAssembly exporter in run mode and includes the local
`annual_loss` package as a browser-installable wheel. Explicit notebook dependencies
cover NumPy, SciPy, Plotly, and Marimo. The generated runtime configuration enables
startup because the pinned exporter otherwise resets it to disabled. This affects
initialization only; annual-loss calculations still require the Calculate action.

WebAssembly uses 32-bit array indices. Annual-loss grouping converts validated
event counts to NumPy's platform index type before `repeat` and `bincount`;
64-bit counts remain in use for workload totals. The same safety limits are checked
before narrowing, so this portability fix changes neither draws nor model semantics.

Deployment is gated on Python checks and Chromium/Firefox tests served at the real
Pages path. Browser tests cover interactive calculations, validation, editors,
charts, and report copying. Identical inputs and seeds must repeat within a given
browser numerical environment. Pyodide may use different package versions from the
native locked environment, so cross-environment sample equality is not a contract.

Only a successful `main` build is deployed. If live verification fails, restore the
legacy tag's tree and deployment workflow in a new commit and redeploy it; never
force-push or delete history. Keep the current site running until browser acceptance
passes on the migration branch.

## Idiomatic Marimo design

- Use `app.py` as a plain-Python, Git-diffable notebook with small cells and explicit
  dependencies.
- Keep trusted calculations in a normal `annual_loss` package so unit tests do not
  depend on notebook execution or browser state.
- Use Marimo controls and forms for distribution parameters, mode choices,
  method-aware scenario editing, panelists, chart options, and calculation
  submission. Scenario and panelist rows use stable IDs and remain visible together
  in expanded vertical lists. Each form reveals only the parameters used by its
  selected method or distribution while retaining hidden values. Let dataflow update
  inexpensive previews and narrative outputs.
- Treat the Calculate button as a snapshot boundary: validate current UI values,
  create immutable model inputs, run with an explicit seed, and retain those results
  until the next calculation.
- Render charts with Plotly and keep executive-summary generation as pure Python so
  displayed and copied text share the same tested source.

## Required verification

Tests should cover exact fitting formulas; SciPy quantiles; PERT support; validation;
formatting; empirical CDF compression and monotonicity; percentile interpolation;
modeled ranges; report content; fixed-seed determinism; finite, non-negative samples;
independent event costs; zero-event years; all distribution pairings; paired scenario
aggregation; linked mode transitions; panel add/delete state, averages, and sample
standard deviations; adaptive round counts; and each workload rejection boundary.

Acceptance is based on exact deterministic assertions where appropriate and
fixed-seed statistical tolerances for sampled moments and quantiles. CI also runs
Ruff, pytest, Marimo's strict notebook checker, and a headless application startup
smoke test.
