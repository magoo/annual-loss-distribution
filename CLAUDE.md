# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A client-side web application for risk quantification using expert probability distribution elicitation. Users input parameters for incident frequency and incident cost (both lognormal), and the app derives an annual loss distribution via Monte Carlo simulation.

The page layout: a Plotly.js chart (top) showing the distribution, with configuration controls below. The chart updates reactively without page refresh. Users can toggle between PDF (density) and CDF (cumulative) views.

### Sections and Parameters

Three tabs (sections):

- **Frequency** — Lognormal (P50, P95). Incident count per year. No dollar formatting.
- **Cost** — Lognormal (P50, P95). Incident cost. Dollar-formatted.
- **Annual Loss** — No user inputs. 10,000 Monte Carlo samples: `frequency × cost` pairwise. Dollar-formatted.

Both frequency and cost parameters persist across tab switches.

### Panel Mode

A "Panel Mode" toggle lets users input parameters from multiple experts. The app averages all submitted parameters to produce the final distribution inputs. When active, an analytics section displays min, max, standard deviation, and average across panelists. On the Annual Loss tab, panelist rows are hidden and two analytics tables (one for frequency, one for cost) are shown.

## Stack

- **Svelte 5** (runes) + **Vite** (client-side only, no backend)
- **Plotly.js** (`plotly.js-basic-dist-min`) for charting
- **jStat** for distribution math
- All computation happens in the browser

## Commands

- `nvm use 22` — required before running commands (Node ≥22, see `.nvmrc`)
- `npm run dev` — start dev server
- `npm run build` — production build
- `npm run preview` — preview production build

## Architecture

Reactive data flow: User Input → `$state` (parameters) → `$derived` (validation + computation) → `$effect` (Plotly.react)

All math is pure JS in `src/lib/math/` (no Svelte dependencies). UI state lives in `src/lib/state/app-state.svelte.js` using Svelte 5 runes, exported via `getState()`.

State model: Two persistent param objects (`frequencyParams`, `costParams`) that survive tab switches. The active section determines which params are displayed/edited. The Annual Loss tab computes chart data from both param sets via Monte Carlo simulation.

### Directory structure

```
src/
  main.js                             # Entry point
  App.svelte                          # Root layout
  app.css                             # Design system (CSS custom properties)
  lib/
    math/
      distributions.js                # SECTIONS metadata + computeDistribution dispatcher
      lognormal.js                     # P50/P95 → mu/sigma
      monte-carlo.js                   # MC simulation: frequency × cost → annual loss
      sampling.js                      # generateXValues(lower, upper, n)
      validation.js                    # Per-section validation rules
    state/
      app-state.svelte.js             # Central reactive state (dual params, MC-derived chart)
    components/
      PlotlyChart.svelte              # Thin Plotly wrapper (conditional dollar formatting)
      DistributionSelector.svelte     # Tab bar (Frequency | Cost | Annual Loss)
      ParameterInputs.svelte          # Parameter form per section
      ParameterField.svelte           # Single validated numeric input
      ViewToggle.svelte               # PDF/CDF segmented control
      PanelMode.svelte                # Panel mode container
      PanelModeToggle.svelte          # Toggle switch
      PanelistRow.svelte              # Single panelist inputs (per-section params)
      PanelAnalytics.svelte           # Summary statistics table (section-aware formatting)
```
