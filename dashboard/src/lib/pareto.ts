import type { RunMetrics, MetricConfig } from '../types';

/**
 * Checks if runA dominates runB for the given metric configurations
 * Run A dominates run B if:
 * - A is better or equal on all metrics
 * - A is strictly better on at least one metric
 */
export function dominates(
  runA: RunMetrics,
  runB: RunMetrics,
  metricConfigs: MetricConfig[]
): boolean {
  let betterInAtLeastOne = false;

  for (const config of metricConfigs) {
    const valueA = runA.metrics[config.key];
    const valueB = runB.metrics[config.key];

    // If either value is missing, cannot determine dominance
    if (valueA === undefined || valueB === undefined) {
      return false;
    }

    // Compare based on optimization direction
    if (config.direction === 'maximize') {
      if (valueA < valueB) {
        // A is worse than B on this metric
        return false;
      }
      if (valueA > valueB) {
        // A is better than B on this metric
        betterInAtLeastOne = true;
      }
    } else {
      // minimize
      if (valueA > valueB) {
        // A is worse than B on this metric
        return false;
      }
      if (valueA < valueB) {
        // A is better than B on this metric
        betterInAtLeastOne = true;
      }
    }
  }

  return betterInAtLeastOne;
}

/**
 * Calculates the Pareto frontier for a set of runs
 * Returns a set of run IDs that are on the Pareto frontier
 *
 * A run is on the Pareto frontier if no other run dominates it
 */
export function calculateParetoFrontier(
  runs: RunMetrics[],
  metricConfigs: MetricConfig[]
): Set<string> {
  const paretoRunIds = new Set<string>();

  // For each run, check if any other run dominates it
  for (const runA of runs) {
    let isDominated = false;

    for (const runB of runs) {
      // Skip comparing with itself
      if (runA.runId === runB.runId) {
        continue;
      }

      // Check if runB dominates runA
      if (dominates(runB, runA, metricConfigs)) {
        isDominated = true;
        break;
      }
    }

    // If no run dominates runA, it's on the Pareto frontier
    if (!isDominated) {
      paretoRunIds.add(runA.runId);
    }
  }

  return paretoRunIds;
}
