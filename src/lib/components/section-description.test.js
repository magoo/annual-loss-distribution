import { describe, expect, it } from 'vitest';
import { getSectionDescription } from './section-description.js';
import { computeDistribution } from '../math/distributions.js';
import { interpolatePercentile } from '../math/percentile.js';
import { formatCompact } from '../math/formatting.js';

const baseFrequencyParams = {
  p50: 6,
  p95: 18,
  p99: 30,
  min: 2,
  mode: 8,
  max: 24,
};

const baseCostParams = {
  p50: 120000,
  p95: 700000,
  p99: 1500000,
  min: 25000,
  mode: 150000,
  max: 900000,
};

const baseChartData = {
  x: [0, 100, 200],
  yCdf: [0, 0.5, 1],
};

function expectedIncidentIntervalText(params, distType, confidenceLevel = 90) {
  const chartData = computeDistribution('frequency', params, null, distType);
  const lowerP = (100 - confidenceLevel) / 2 / 100;
  const upperP = 1 - lowerP;
  const lower = interpolatePercentile(chartData.x, chartData.yCdf, lowerP);
  const upper = interpolatePercentile(chartData.x, chartData.yCdf, upperP);
  return {
    lower: formatCompact(Math.max(0, Math.round(lower)), false),
    upper: formatCompact(Math.max(0, Math.round(upper)), false),
  };
}

function expectedCostIntervalText(params, distType, confidenceLevel = 90) {
  const chartData = computeDistribution('cost', params, null, distType);
  const lowerP = (100 - confidenceLevel) / 2 / 100;
  const upperP = 1 - lowerP;
  const lower = interpolatePercentile(chartData.x, chartData.yCdf, lowerP);
  const upper = interpolatePercentile(chartData.x, chartData.yCdf, upperP);
  return {
    lower: formatCompact(lower, true),
    upper: formatCompact(upper, true),
  };
}

describe('getSectionDescription', () => {
  it('returns guidance for frequency mode', () => {
    const model = getSectionDescription({
      activeSection: 'frequency',
    });

    expect(model.mode).toBe('plain');
    expect(model.text).toContain('estimate how many incidents you expect');
    expect(model.text).toContain('Frequency input');
  });

  it('returns guidance for cost mode', () => {
    const model = getSectionDescription({
      activeSection: 'cost',
    });

    expect(model.mode).toBe('plain');
    expect(model.text).toContain('typical and high-end cost of a single incident');
    expect(model.text).toContain('Cost input');
  });

  it('returns executive summary blocks for default calculate mode', () => {
    const model = getSectionDescription({
      activeSection: 'loss',
      frequencyParams: baseFrequencyParams,
      costParams: baseCostParams,
      frequencyDistType: 'lognormal',
      costDistType: 'pareto',
      chartData: baseChartData,
      confidenceLevel: 90,
    });

    expect(model.mode).toBe('executive');
    expect(model.title).toBe('Executive Summary');
    expect(model.intro).toContain('100,000-sample Monte Carlo');

    const simulationSection = model.sections.find((section) => section.title === 'Simulation Setup');
    expect(simulationSection?.bullets).toContain('Simulation mode: 100,000-sample distribution-based Monte Carlo');

    const frequencySection = model.sections.find((section) => section.title === 'Frequency Inputs');
    expect(frequencySection?.bullets).toContain('Distribution: Lognormal');
    expect(frequencySection?.bullets).toContain('P50 (typical): 6');
    expect(frequencySection?.bullets).toContain('P99 (extreme): 30');

    const costSection = model.sections.find((section) => section.title === 'Cost Inputs');
    expect(costSection?.bullets).toContain('Distribution: Pareto');
    expect(costSection?.bullets).toContain('P50 (typical): $120K');

    const incidentInterval = expectedIncidentIntervalText(baseFrequencyParams, 'lognormal', 90);
    const costInterval = expectedCostIntervalText(baseCostParams, 'pareto', 90);
    expect(model.confidenceNarrative).toHaveLength(1);
    expect(model.confidenceNarrative[0]).toContain('90% belief');
    expect(model.confidenceNarrative[0]).toContain(`between ${incidentInterval.lower} and ${incidentInterval.upper} incidents`);
    expect(model.confidenceNarrative[0]).toContain(`at costs between ${costInterval.lower} and ${costInterval.upper} per incident`);
    expect(model.confidenceNarrative[0]).toContain('expected total annual loss between $10 and $190');
    expect(model.sections.some((section) => section.title === 'Annual Loss Confidence Interval')).toBe(false);
  });

  it('returns scenario-based summary when both sides use scenarios', () => {
    const model = getSectionDescription({
      activeSection: 'loss',
      frequencyScenarioMode: true,
      costScenarioMode: true,
      scenarios: [
        {
          name: 'Ransomware',
          frequencyMethod: 'odds',
          frequencyParams: { odds: 4 },
          costDistType: 'lognormal',
          costParams: { p50: 100000, p95: 1000000, p99: 5000000 },
        },
        {
          name: 'Vendor outage',
          frequencyMethod: 'odds',
          frequencyParams: { odds: 6 },
          costDistType: 'lognormal',
          costParams: { p50: 50000, p95: 500000, p99: 2000000 },
        },
      ],
    });

    expect(model.intro).toContain('scenario-based Monte Carlo');
    const simulationSection = model.sections.find((section) => section.title === 'Simulation Setup');
    expect(simulationSection?.bullets).toContain('Simulation mode: 10,000-round scenario-based Monte Carlo');
    expect(simulationSection?.bullets).toContain('Scenario set: 2 threat scenarios (Ransomware, Vendor outage)');
    expect(model.confidenceNarrative[0]).not.toContain('n/a');
  });

  it('returns hybrid summary for frequency scenarios and distribution-based cost', () => {
    const model = getSectionDescription({
      activeSection: 'loss',
      frequencyScenarioMode: true,
      costScenarioMode: false,
      costDistType: 'pert',
      costParams: baseCostParams,
      scenarios: [{ name: 'Phishing surge' }],
    });

    expect(model.intro).toContain('hybrid Monte Carlo model');

    const frequencySection = model.sections.find((section) => section.title === 'Frequency Inputs');
    expect(frequencySection?.bullets).toContain('Frequency method: Scenario-based sampling from 1 threat scenario');

    const costSection = model.sections.find((section) => section.title === 'Cost Inputs');
    expect(costSection?.bullets).toContain('Distribution: PERT');
    expect(costSection?.bullets).toContain('Minimum: $25K');
  });

  it('returns hybrid summary for distribution-based frequency and scenario cost', () => {
    const model = getSectionDescription({
      activeSection: 'loss',
      frequencyScenarioMode: false,
      costScenarioMode: true,
      frequencyDistType: 'pert',
      frequencyParams: baseFrequencyParams,
      scenarios: [{ name: 'Insider event' }, { name: 'Credential replay' }],
    });

    const frequencySection = model.sections.find((section) => section.title === 'Frequency Inputs');
    expect(frequencySection?.bullets).toContain('Distribution: PERT');
    expect(frequencySection?.bullets).toContain('Most likely: 8');

    const costSection = model.sections.find((section) => section.title === 'Cost Inputs');
    expect(costSection?.bullets).toContain('Cost method: Scenario-based sampling from 2 threat scenarios');
  });

  it('includes copy-ready multiline text for executive summary', () => {
    const model = getSectionDescription({
      activeSection: 'loss',
      frequencyParams: baseFrequencyParams,
      costParams: baseCostParams,
    });

    expect(model.copyText).toContain('Executive Summary');
    expect(model.copyText).toContain('Confidence Interval Summary:');
    expect(model.copyText).toContain('There is a 90% belief that between');
    expect(model.copyText).toContain('at costs between');
    expect(model.copyText).toContain('Simulation Setup:');
    expect(model.copyText).toContain('- Simulation mode: 100,000-sample distribution-based Monte Carlo');
    expect(model.copyText).not.toContain('Annual Loss Confidence Interval:');
  });
});
