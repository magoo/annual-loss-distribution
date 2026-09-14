# Annual Loss Distribution

Explore how often security incidents might happen, how much each might cost, and
what those assumptions could mean for a year's total losses. Annual Loss
Distribution helps security practitioners discuss uncertainty and communicate risk
with charts and a copyable executive summary.

**[Open Annual Loss Distribution](https://magoo.github.io/annual-loss-distribution/)**

No installation or account is needed. Use a current Chromium or Firefox browser.
The first load can take a little longer while the app downloads its Python runtime
and packages from the same website.

## Try your first analysis

Start with the app's example inputs to learn the workflow, then replace them with
your own estimates. The examples are a starting point, not recommended estimates
for your organization.

1. Review **Frequency**: how many incidents could occur in a year. Keep
   **Direct estimate** selected for your first run.
2. Review **Cost**: how much one incident could cost, in dollars. For the default
   lognormal model, **P50** is the median: half the modeled outcomes fall at or
   below it. **P95** is a high estimate, with 95% of outcomes at or below it.
   It is not a maximum. Frequency uses these percentiles in the same way.
3. Select **Calculate / Recalculate annual loss**. The app repeatedly samples
   possible years, draws a separate cost for each incident, and adds those costs
   to get each year's total. This is called Monte Carlo simulation.
4. Inspect the annual-loss chart and modeled range, then use the executive summary
   to share the assumptions and results.
5. Give your work a name under **Your analyses**, and choose **Download analysis**
   to keep a backup.

Press Enter or leave a numeric field to apply an edit. After changing assumptions,
calculate again to update annual-loss results; editing alone does not rerun them.

When you need more detail, **Expert panel** lets you enter several people's
estimates and uses the average of each input parameter. **Threat scenarios** lets
you pair a frequency and cost model for each named threat, then add their yearly
losses together. Lognormal, modified PERT, and Pareto models support different
assumptions about the spread of outcomes; the forms explain the inputs they need.

## Read the results

- **Histogram** shows where simulated annual losses are concentrated. Frequency
  and cost previews show the shapes of their distributions.
- **CDF** means cumulative distribution function. At a given loss amount, the
  curve shows the modeled probability of losing that amount or less. For example,
  95% at $500,000 means a modeled 5% chance of exceeding $500,000 in a year.
- **Central range (%)** selects the middle portion of modeled outcomes. A 90%
  range runs from the 5th to the 95th percentile; outcomes can fall outside it.
  This is a modeled outcome range, not a confidence interval for the accuracy of
  your estimates.
- **Outcome percentile** changes how much of the chart is visible so you can
  inspect its main shape. It does not remove larger losses from the simulation.

The results reflect your assumptions. They are not a forecast or a substitute for
professional risk judgment. The app reports the random seed and number of simulated
years so a calculation can be repeated with the same inputs and software versions.

## Save your work and protect your data

On the public website, calculations run in your browser and entered estimates are
not uploaded. When you run the app locally, Python performs calculations on your
computer. There is no application backend service, account system, or telemetry.

**Your analyses** lets you create, rename, duplicate, switch, and delete analyses.
The app saves inputs, chart settings, and unfinished typing in your browser profile
and reopens the last-used analysis. **Saved** confirms a durable browser save;
**Not saved** means you should download your work before closing.

- **Download analysis** saves one analysis as a readable `.analysis.json` file.
- **Back up all analyses** downloads the readable library, including drafts.
- **Import backup** adds analyses without overwriting existing ones.
- **Recover previous session** restores an earlier checkpoint as a separate analysis.

Browser saves are not encrypted by the app or synchronized between devices.
Clearing site data or losing your browser profile can remove them. Use downloaded
backups to move work between browsers, devices, or the public and local versions.
Backups contain inputs, not calculated annual-loss results: calculate again after
opening or switching an analysis. Only one tab can edit an analysis at a time.

Backups may contain sensitive estimates and expert names. Keep them outside this
source repository, or in its ignored `analysis-backups/` or `private/` directory.
See the [backup and recovery guide](ANALYSIS_BACKUPS.md) for save-status details,
recovery limits, and file-format compatibility.

## Run on your computer

Install [Git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/), and Python 3.11
or newer. Then run:

```bash
git clone https://github.com/magoo/annual-loss-distribution.git
cd annual-loss-distribution
uv sync --locked
uv run marimo run app.py
```

Open the local address shown in your terminal. This starts the application with
editable analysis inputs. For notebook editing, development checks, architecture,
and GitHub Pages builds, see the [contributor guide](CONTRIBUTING.md).

## Contributing

Bug reports, clearer explanations, and code contributions are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and checks. When reporting a
modeling issue, include sanitized example inputs and the simulation seed; keep
confidential scenarios and real incident data out of public issues.

The [model specification](docs/source-review.md) explains the calculations,
validation limits, and compatibility with the original application.

## Attribution and license

Built with Python and [Marimo](https://marimo.io/), this implementation is derived
from the ISC-licensed
[original application](https://github.com/magoo/annual-loss-distribution/tree/53c864df0c9b7a8ef866858c7c27e2d43a67b864)
by Ryan McGeehan. See [LICENSE](LICENSE).

The original Svelte/JavaScript application remains available in the repository
history and the `legacy-svelte-2026-09-08` tag.
