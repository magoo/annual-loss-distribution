<script>
  import { onMount } from 'svelte';
  import { interpolatePercentile } from '../math/percentile.js';

  let {
    chartData,
    view,
    useDollars = true,
    activeSection = 'frequency',
    focusPercentile = 99.5,
  } = $props();

  let containerEl;
  let Plotly;
  let plotlyReady = $state(false);

  onMount(async () => {
    Plotly = (await import('plotly.js-basic-dist-min')).default;
    plotlyReady = true;
  });

  function formatXValue(xVal) {
    if (useDollars) {
      return '$' + xVal.toLocaleString('en-US', { maximumFractionDigits: 0 });
    }
    return xVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function interpolateCdfAtX(xVals, yCdfVals, targetX) {
    if (!xVals || !yCdfVals || xVals.length === 0 || yCdfVals.length === 0) return 0;
    if (targetX <= xVals[0]) return yCdfVals[0];
    if (targetX >= xVals[xVals.length - 1]) return yCdfVals[yCdfVals.length - 1];

    for (let i = 1; i < xVals.length; i++) {
      if (xVals[i] >= targetX) {
        const dx = xVals[i] - xVals[i - 1];
        if (dx === 0) return yCdfVals[i];
        const t = (targetX - xVals[i - 1]) / dx;
        return yCdfVals[i - 1] + t * (yCdfVals[i] - yCdfVals[i - 1]);
      }
    }

    return yCdfVals[yCdfVals.length - 1];
  }

  function buildHoverText(xVal, cdfVal, extraLine = '') {
    const valueLabel = formatXValue(xVal);
    const percentile = (Math.max(0, Math.min(1, cdfVal)) * 100).toFixed(1);
    const lines = [valueLabel];
    if (extraLine) lines.push(extraLine);
    lines.push(`Percentile: ${percentile}%`);

    if (activeSection === 'loss') {
      const exceedance = ((1 - Math.max(0, Math.min(1, cdfVal))) * 100).toFixed(1);
      lines.push(`${exceedance}% chance of losing more than ${valueLabel}`);
    }

    return lines.join('<br>');
  }

  function computeFocusedRange(data, upperPercentile) {
    if (!data?.x || !data?.yCdf || data.x.length === 0 || data.yCdf.length === 0) return null;
    if (!isFinite(upperPercentile) || upperPercentile >= 1) return null;

    let lower = interpolatePercentile(data.x, data.yCdf, 0.005);
    let upper = interpolatePercentile(data.x, data.yCdf, upperPercentile);

    if (!isFinite(lower) || !isFinite(upper)) return null;

    if (useDollars && lower <= 0) {
      const firstPositive = data.x.find((v) => v > 0);
      if (!firstPositive) return null;
      lower = firstPositive;
    }

    if (upper <= lower) return null;
    return { lower, upper };
  }

  $effect(() => {
    if (!plotlyReady || !containerEl) return;

    if (!chartData) {
      Plotly.react(containerEl, [], {
        xaxis: { visible: false },
        yaxis: { visible: false },
        annotations: [{
          text: 'Enter valid parameters to see the distribution',
          xref: 'paper',
          yref: 'paper',
          x: 0.5,
          y: 0.5,
          showarrow: false,
          font: { size: 15, color: '#9ca3af', family: 'Inter, sans-serif' },
        }],
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 20, r: 20, b: 20, l: 20 },
      }, { displayModeBar: false, responsive: true });
      return;
    }

    const isPdf = view === 'pdf';
    const isLossSection = activeSection === 'loss';
    const canFocusRange = true;
    const upperPercentile = Math.max(0.95, Math.min(1, Number(focusPercentile) / 100));
    const focusedRange = canFocusRange ? computeFocusedRange(chartData, upperPercentile) : null;

    // Histogram mode (scenario MC) vs standard continuous mode
    if (chartData.isHistogram) {
      let trace, layout;

      if (isPdf) {
        const isIntegerData = chartData.samples.every((v) => Number.isInteger(v));

        if (useDollars) {
          // Dollar data spans orders of magnitude — pre-compute log-spaced bins
          // because Plotly's histogram always bins in linear space.
          const pos = chartData.samples.filter((v) => v > 0);
          if (pos.length > 0) {
            const sorted = Float64Array.from(pos).sort();
            const lo = sorted[Math.floor(sorted.length * 0.005)] || sorted[0];
            const hi = sorted[Math.min(Math.floor(sorted.length * 0.995), sorted.length - 1)];
            const logLo = Math.log10(lo);
            const logHi = Math.log10(hi);
            const numBins = 60;
            const logStep = (logHi - logLo) / numBins;

            const edges = [];
            for (let i = 0; i <= numBins; i++) {
              edges.push(Math.pow(10, logLo + i * logStep));
            }

            const counts = new Array(numBins).fill(0);
            let si = 0;
            for (let b = 0; b < numBins; b++) {
              const right = edges[b + 1];
              while (si < sorted.length && sorted[si] <= right) {
                si++;
                counts[b]++;
              }
            }

            const centers = [];
            const widths = [];
            for (let b = 0; b < numBins; b++) {
              centers.push(Math.sqrt(edges[b] * edges[b + 1]));
              widths.push(edges[b + 1] - edges[b]);
            }

            const total = chartData.samples.length;
            const hovertext = centers.map((center, i) => {
              const pct = ((counts[i] / total) * 100).toFixed(1);
              if (isLossSection) {
                const cdfAtCenter = interpolateCdfAtX(chartData.x, chartData.yCdf, center);
                return buildHoverText(center, cdfAtCenter, `Bin share: ${pct}%`);
              }
              const label = '$' + center.toLocaleString('en-US', { maximumFractionDigits: 0 });
              return `${label} (${pct}%)`;
            });

            trace = {
              x: centers,
              y: counts,
              type: 'bar',
              width: widths,
              hoverinfo: 'text',
              hovertext,
              marker: {
                color: 'rgba(247, 37, 133, 0.5)',
                line: { color: '#f72585', width: 1 },
              },
            };
          }
        } else if (isIntegerData) {
          // Integer data (frequency): count occurrences of each value
          const valueCounts = new Map();
          for (const v of chartData.samples) {
            valueCounts.set(v, (valueCounts.get(v) || 0) + 1);
          }
          const keys = Array.from(valueCounts.keys()).sort((a, b) => a - b);
          const total = chartData.samples.length;
          const hovertext = keys.map((k) => {
            const count = valueCounts.get(k);
            const pct = ((count / total) * 100).toFixed(1);
            if (isLossSection) {
              const cdfAtK = interpolateCdfAtX(chartData.x, chartData.yCdf, k);
              return buildHoverText(k, cdfAtK, `Occurrences: ${pct}%`);
            }
            return `${k} incidents (${pct}%)`;
          });
          trace = {
            x: keys,
            y: keys.map((k) => valueCounts.get(k)),
            type: 'bar',
            width: 0.8,
            hoverinfo: 'text',
            hovertext,
            marker: {
              color: 'rgba(247, 37, 133, 0.5)',
              line: { color: '#f72585', width: 1 },
            },
          };
        }

        if (!trace) {
          // Fallback for non-integer, non-dollar continuous data
          trace = {
            x: chartData.samples,
            type: 'histogram',
            marker: {
              color: 'rgba(247, 37, 133, 0.5)',
              line: { color: '#f72585', width: 1 },
            },
          };
        }
      } else {
        // Empirical CDF line
        const hovertext = isLossSection
          ? chartData.x.map((xVal, i) => buildHoverText(xVal, chartData.yCdf[i]))
          : null;

        trace = {
          x: chartData.x,
          y: chartData.yCdf,
          type: 'scatter',
          mode: 'lines',
          line: { color: '#4361ee', width: 2.5, shape: 'spline' },
          ...(hovertext ? { hoverinfo: 'text', hovertext } : {}),
        };
      }

      const xAxisTitle = activeSection === 'frequency' ? 'Incidents per Year'
        : activeSection === 'cost' ? 'Cost per Incident'
        : 'Annual Loss';

      layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 16, r: 24, b: 56, l: 56 },
        xaxis: {
          title: {
            text: xAxisTitle,
            font: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
          },
          ...(useDollars ? { type: 'log' } : {}),
          ...(focusedRange
            ? {
                range: useDollars
                  ? [Math.log10(focusedRange.lower), Math.log10(focusedRange.upper)]
                  : [focusedRange.lower, focusedRange.upper],
              }
            : {}),
          gridcolor: '#f0f0f0',
          zerolinecolor: '#e5e7eb',
          tickprefix: useDollars ? '$' : '',
          tickformat: useDollars ? ',.0f' : ',.2f',
          tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
        },
        yaxis: {
          title: {
            text: isPdf ? 'Occurrences' : 'Cumulative Probability',
            font: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
          },
          gridcolor: '#f0f0f0',
          zerolinecolor: '#e5e7eb',
          tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
          ...(!isPdf ? { range: [0, 1.05] } : {}),
        },
        bargap: 0,
        showlegend: false,
        hovermode: 'closest',
        hoverlabel: {
          bgcolor: '#1a1a2e',
          font: { color: '#fff', size: 13, family: 'Inter, sans-serif' },
        },
      };

      Plotly.newPlot(containerEl, [trace], layout, { displayModeBar: false, responsive: true });
      return;
    }

    const yValues = isPdf ? chartData.yPdf : chartData.yCdf;

    // Build custom hover text with conditional formatting
    const hovertext = chartData.x.map((xVal, i) => {
      const cdfVal = chartData.yCdf[i];
      if (isLossSection) {
        return buildHoverText(xVal, cdfVal);
      }

      const valStr = formatXValue(xVal);
      const pct = (cdfVal * 100).toFixed(1);
      return `${valStr}<br>Percentile: ${pct}%`;
    });

    const trace = {
      x: chartData.x,
      y: yValues,
      type: 'scatter',
      mode: 'lines',
      hoverinfo: 'text',
      hovertext,
      line: {
        color: isPdf ? '#f72585' : '#4361ee',
        width: isPdf ? 2 : 2.5,
        shape: 'spline',
      },
      ...(isPdf ? {
        fill: 'tozeroy',
        fillcolor: 'rgba(247, 37, 133, 0.12)',
      } : {}),
    };

    const layout = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { t: 16, r: 24, b: 40, l: 56 },
      xaxis: {
        ...(focusedRange ? { range: [focusedRange.lower, focusedRange.upper] } : {}),
        gridcolor: '#f0f0f0',
        zerolinecolor: '#e5e7eb',
        tickprefix: useDollars ? '$' : '',
        tickformat: useDollars ? ',.0f' : ',.2f',
        tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
      },
      yaxis: {
        title: {
          text: isPdf ? 'Likelihood' : 'Cumulative Probability',
          font: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
        },
        gridcolor: '#f0f0f0',
        zerolinecolor: '#e5e7eb',
        tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
        ...(isPdf ? { showticklabels: false } : { range: [0, 1.05] }),
      },
      showlegend: false,
      hovermode: 'closest',
      hoverlabel: {
        bgcolor: '#1a1a2e',
        font: { color: '#fff', size: 13, family: 'Inter, sans-serif' },
      },
    };

    Plotly.react(containerEl, [trace], layout, { displayModeBar: false, responsive: true });
  });
</script>

<div class="chart-container">
  <div bind:this={containerEl} class="chart"></div>
</div>

<style>
  .chart-container {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    overflow: hidden;
  }
  .chart {
    width: 100%;
    height: 100%;
  }
</style>
