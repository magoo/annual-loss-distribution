<script>
  import { onMount } from 'svelte';
  import { computeDistribution } from '../math/distributions.js';
  import { validate } from '../math/validation.js';

  let { section, distType, params } = $props();

  let containerEl;
  let Plotly;
  let plotlyReady = $state(false);

  const isCost = $derived(section === 'cost');

  function computeBernoulliBar(params) {
    const odds = params?.odds;
    if (odds == null || isNaN(odds) || odds <= 0) return null;
    const p = 1 / odds;
    return { isBernoulli: true, x: [0, 1], y: [1 - p, p] };
  }

  const chartData = $derived.by(() => {
    // Validate first
    const errors = validate(section, params, distType);
    if (Object.keys(errors).length > 0) return null;

    if (distType === 'odds') {
      return computeBernoulliBar(params);
    }
    return computeDistribution(section, params, null, distType);
  });

  onMount(async () => {
    Plotly = (await import('plotly.js-basic-dist-min')).default;
    plotlyReady = true;
    return () => {
      if (containerEl) Plotly.purge(containerEl);
    };
  });

  $effect(() => {
    if (!plotlyReady || !containerEl) return;

    if (!chartData) {
      Plotly.react(containerEl, [], {
        xaxis: { visible: false },
        yaxis: { visible: false },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 2, r: 4, b: 14, l: 4 },
        height: 100,
      }, { staticPlot: true, displayModeBar: false, responsive: true });
      return;
    }

    let trace, layout;

    if (chartData.isBernoulli) {
      trace = {
        x: chartData.x,
        y: chartData.y,
        type: 'bar',
        marker: {
          color: ['rgba(67, 97, 238, 0.4)', 'rgba(247, 37, 133, 0.5)'],
          line: { color: ['#4361ee', '#f72585'], width: 1 },
        },
        width: 0.6,
        hoverinfo: 'none',
      };
      layout = {
        height: 100,
        margin: { t: 2, r: 4, b: 14, l: 4 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: {
          tickvals: [0, 1],
          ticktext: ['0', '1'],
          tickfont: { size: 8, color: '#9ca3af' },
          showgrid: false,
          zeroline: false,
        },
        yaxis: { visible: false, showgrid: false },
        showlegend: false,
        hovermode: false,
        bargap: 0.3,
      };
    } else {
      trace = {
        x: chartData.x,
        y: chartData.yPdf,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#f72585', width: 1.5, shape: 'spline' },
        fill: 'tozeroy',
        fillcolor: 'rgba(247, 37, 133, 0.12)',
        hoverinfo: 'none',
      };
      layout = {
        height: 100,
        margin: { t: 2, r: 4, b: 14, l: 4 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: {
          visible: true,
          nticks: 3,
          tickfont: { size: 8, color: '#9ca3af' },
          tickprefix: isCost ? '$' : '',
          tickformat: isCost ? ',.0f' : '',
          showgrid: false,
          zeroline: false,
        },
        yaxis: { visible: false, showgrid: false },
        showlegend: false,
        hovermode: false,
      };
    }

    Plotly.react(containerEl, [trace], layout, { staticPlot: true, displayModeBar: false, responsive: true });
  });
</script>

<div class="mini-chart-container">
  <div bind:this={containerEl} class="mini-chart"></div>
</div>

<style>
  .mini-chart-container {
    width: 100%;
    height: 100px;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .mini-chart {
    width: 100%;
    height: 100%;
  }
</style>
