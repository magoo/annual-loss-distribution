# Annual Loss Distribution

A client-side web app for quantifying risk using expert probability elicitation. Users provide estimates for how often an incident occurs (frequency) and how much it costs (cost), and the app derives an annual loss distribution via Monte Carlo simulation.

**[Live demo](https://magoo.github.io/annual-loss-distribution/)**

## How it works

Risk analysts estimate two lognormal distributions using P50 (median) and P95 (95th percentile) inputs:

- **Frequency** — How many incidents per year?
- **Cost** — How much does each incident cost?

The app multiplies 10,000 paired samples from these distributions to produce an **Annual Loss** distribution, displayed as either a PDF (density) or CDF (cumulative) chart.

### Panel Mode

Multiple experts can submit independent estimates. The app averages their parameters and shows summary statistics (min, max, standard deviation, average) across panelists.

## Stack

- [Svelte 5](https://svelte.dev/) with runes for reactive state
- [Plotly.js](https://plotly.com/javascript/) for charting
- [jStat](https://jstat.github.io/) for distribution math
- [Vite](https://vite.dev/) for builds
- Everything runs in the browser — no backend

## Development

Requires Node 22+ (see `.nvmrc`).

```bash
npm install
npm run dev       # Start dev server at localhost:5173
npm test          # Run tests
npm run build     # Production build
```

## License

Copyright Ryan McGeehan. ISC License.
