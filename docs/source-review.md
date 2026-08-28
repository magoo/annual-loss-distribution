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

The user workflow has three ordered sections: Frequency, Cost, and Calculate. Soft
workflow gates encourage review in that order while allowing a user to open a later
step intentionally.

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

### Scenario and hybrid annual loss

Scenario simulations target 10,000 years and use the same lower round bound and work
ceilings when costs are required.

- With scenario frequency and scenario cost, each scenario independently produces
  its annual count and every event uses that same scenario's cost distribution.
- With scenario frequency and distribution cost, scenario counts are summed and
  every realized event uses the shared cost distribution.
- With distribution frequency and scenario cost, a scenario is selected uniformly
  for each realized event and its cost distribution is sampled.
- `1 in N years` is a Bernoulli trial with annual probability `1/N`; distribution
  frequencies are rounded to non-negative integer counts.

The upstream simulation module already implements these hybrid combinations, but
the Svelte application has one global scenario-mode flag. Consequently, users can
only select all-scenario or all-distribution behavior through the UI.

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
3. Expose Frequency and Cost modes independently in Marimo so all four combinations
   (distribution/distribution, scenario/scenario, and both hybrids) are reachable.
   Preserve the upstream hybrid sampling behavior described above.
4. Keep panel aggregation intentionally simple: arithmetic means of elicited fields
   drive the fitted model, while analytics use sample standard deviation. This is
   parameter aggregation, not mathematical pooling of expert distributions.
5. Gate full Monte Carlo work behind an explicit Calculate/Recalculate action. The
   upstream derives chart data reactively, which is natural in Svelte but can repeat
   expensive work as inputs change.
6. Keep reporting language precise: say `modeled outcome range`, not statistical
   `confidence interval`. Include the actual seed and effective rounds in result and
   report metadata.
7. Keep all inputs in memory for v1. Persistence, authentication, telemetry,
   deployment, and static export are outside the initial implementation.

## Idiomatic Marimo design

- Use `app.py` as a plain-Python, Git-diffable notebook with small cells and explicit
  dependencies.
- Keep trusted calculations in a normal `annual_loss` package so unit tests do not
  depend on notebook execution or browser state.
- Use Marimo controls and forms for distribution parameters, mode choices, scenario
  rows, panel rows, chart options, and calculation submission. Let dataflow update
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
independent event costs; zero-event years; all distribution pairings; all scenario
and hybrid combinations; panel averages and sample standard deviations; adaptive
round counts; and each workload rejection boundary.

Acceptance is based on exact deterministic assertions where appropriate and
fixed-seed statistical tolerances for sampled moments and quantiles. CI also runs
Ruff, pytest, Marimo's strict notebook checker, and a headless application startup
smoke test.
