const DEFAULT_NUM_POINTS = 500;

/**
 * Build a compact empirical CDF while preserving point mass at zero and the
 * maximum simulated value. Positive values are plotted on a log-spaced grid
 * so heavy-tailed outcomes remain readable.
 *
 * @param {ArrayLike<number>} sortedSamples Samples sorted ascending
 * @param {number} [numPoints]
 * @returns {{ x: number[], yCdf: number[] }}
 */
export function empiricalCdfArrays(sortedSamples, numPoints = DEFAULT_NUM_POINTS) {
  const n = sortedSamples.length;
  if (n === 0) return { x: [], yCdf: [] };

  const first = sortedSamples[0];
  const last = sortedSamples[n - 1];
  if (!Number.isFinite(first) || !Number.isFinite(last)) return { x: [], yCdf: [] };
  if (last <= first) return { x: [first], yCdf: [1] };

  let firstPositiveIndex = 0;
  while (firstPositiveIndex < n && sortedSamples[firstPositiveIndex] <= 0) {
    firstPositiveIndex++;
  }

  const x = [];
  if (firstPositiveIndex > 0) x.push(0);

  const positiveCount = n - firstPositiveIndex;
  if (positiveCount > 0) {
    const positiveLowerIndex = firstPositiveIndex + Math.floor(positiveCount * 0.001);
    const positiveUpperIndex = firstPositiveIndex + Math.min(
      Math.floor(positiveCount * 0.999),
      positiveCount - 1,
    );
    const lower = sortedSamples[positiveLowerIndex];
    const upper = sortedSamples[positiveUpperIndex];

    if (lower > 0 && upper > lower) {
      const gridPoints = Math.max(2, numPoints - x.length - 1);
      const logLower = Math.log(lower);
      const logUpper = Math.log(upper);
      const logStep = (logUpper - logLower) / (gridPoints - 1);
      for (let i = 0; i < gridPoints; i++) {
        if (i === 0) {
          x.push(lower);
        } else if (i === gridPoints - 1) {
          x.push(upper);
        } else {
          x.push(Math.exp(logLower + i * logStep));
        }
      }
    } else {
      x.push(lower);
    }
  }

  // "Full plotted range" should include every simulated outcome, even though
  // the regular grid is focused on the central 99.8% of positive samples.
  if (x.length === 0 || last > x[x.length - 1]) x.push(last);

  const yCdf = [];
  let sampleIndex = 0;
  for (const xValue of x) {
    while (sampleIndex < n && sortedSamples[sampleIndex] <= xValue) sampleIndex++;
    yCdf.push(sampleIndex / n);
  }

  return { x, yCdf };
}
