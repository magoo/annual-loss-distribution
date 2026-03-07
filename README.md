# Annual Loss Distribution

A friendly, browser-based app for turning security risk intuition into a usable annual loss curve.

Instead of wrestling with raw probability math, you can describe how often bad events happen, how much they cost, and let the app run the simulation for you.

**[Live demo](https://magoo.github.io/annual-loss-distribution/)**

## What this app does

- Helps you model **Frequency** (how often incidents happen)
- Helps you model **Cost** (how expensive each incident is)
- Combines both into **Annual Loss** using Monte Carlo simulation
- Lets you work in either:
  - **Distribution mode** (Lognormal, PERT, Pareto)
  - **Scenario Mode** (threat-by-threat scenario modeling)
- Supports **Panel Mode** for multiple expert inputs
- Shows results as **PDF** or **CDF**
- Adds a configurable **confidence interval** summary
- Generates an **executive report** style narrative on the Calculate tab

Everything runs client-side. No backend required.

## How to use it (quick walkthrough)

1. Pick a tab: **Frequency**, **Cost**, or **Calculate**.
2. In Frequency and Cost, choose one modeling option:
   - **Lognormal**: most outcomes are moderate, with occasional bigger spikes
   - **PERT**: you estimate low / likely / high values
   - **Pareto**: you want to emphasize tail risk and rare extremes
   - **Scenario Mode**: model named threat scenarios directly
3. Enter inputs (or use panelists/scenarios).
4. Review the chart and switch between **PDF** and **CDF**.
5. Adjust the confidence slider to see the range statement update.
6. Open **Calculate** to view combined annual loss results and the report summary.

## Modeling modes

### Distribution mode (Lognormal / PERT / Pareto)

Use this when you want a compact model from a few key estimates.

- **Lognormal** and **Pareto** use percentile-style inputs (P50/P95/P99)
- **PERT** uses min / most likely / max
- Inputs are section-aware (Frequency vs Cost)

### Scenario Mode

Use this when you want to model specific threat scenarios (for example, ransomware, social engineering, supply chain, etc.).

- Add/edit/remove scenarios
- Choose per-scenario frequency method and cost distribution
- Optional mini previews per scenario
- Scenario simulations run as a **10,000-round Monte Carlo** process

Scenario mode can be used for Frequency, Cost, or both (hybrid modeling is supported).

### Panel Mode

Use this when multiple SMEs need to contribute.

- Add panelists
- Capture each panelist's estimates
- App computes aggregate parameters and summary analytics

## How the simulation works (plain English)

- In distribution mode, the app samples from your chosen distributions.
- In scenario mode, the app samples events/costs from your scenario definitions.
- For annual loss, it combines frequency and cost behavior over many simulated years.
- Results are shown as either:
  - **PDF**: where outcomes are concentrated
  - **CDF**: probability of being at or below a value

The confidence interval module interpolates from the CDF and expresses the result in a plain-language sentence.

## Current feature highlights

- Frequency / Cost / Calculate workflow
- Integrated mode selector: **Lognormal | PERT | Pareto | Scenario Mode**
- Mode-specific descriptive guidance text
- Scenario editor with optional previews
- Panel analytics support
- Confidence interval slider (50% to 95%)
- Executive report summary on Calculate
- Deterministic seeded Monte Carlo implementation
- Comprehensive math/unit test coverage

## Tech stack

- [Svelte 5](https://svelte.dev/) (runes)
- [Vite](https://vite.dev/)
- [Plotly.js](https://plotly.com/javascript/) for charts
- [jStat](https://jstat.github.io/) for distribution math
- [Vitest](https://vitest.dev/) for tests

## Development

Requires **Node 22+** (see `.nvmrc`).

```bash
npm install
npm run dev      # Start local dev server (usually http://localhost:5173)
npm test         # Run unit tests
npm run build    # Build production assets
npm run preview  # Preview production build locally
```

## License

Copyright Ryan McGeehan.
ISC License.
