<script>
  import { onMount } from 'svelte';

  let { chartData, view, useDollars = true } = $props();

  let containerEl;
  let Plotly;
  let plotlyReady = $state(false);

  onMount(async () => {
    Plotly = (await import('plotly.js-basic-dist-min')).default;
    plotlyReady = true;
  });

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
    const yValues = isPdf ? chartData.yPdf : chartData.yCdf;

    // Build custom hover text with conditional formatting
    const hovertext = chartData.x.map((xVal, i) => {
      let valStr;
      if (useDollars) {
        valStr = '$' + xVal.toLocaleString('en-US', { maximumFractionDigits: 0 });
      } else {
        valStr = xVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
      const pct = (chartData.yCdf[i] * 100).toFixed(1);
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
        gridcolor: '#f0f0f0',
        zerolinecolor: '#e5e7eb',
        tickprefix: useDollars ? '$' : '',
        tickformat: useDollars ? ',.0f' : ',.2f',
        tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
      },
      yaxis: {
        title: {
          text: isPdf ? 'Density' : 'Cumulative Probability',
          font: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
        },
        gridcolor: '#f0f0f0',
        zerolinecolor: '#e5e7eb',
        tickfont: { size: 12, color: '#6b7280', family: 'Inter, sans-serif' },
        ...(isPdf ? {} : { range: [0, 1.05] }),
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
