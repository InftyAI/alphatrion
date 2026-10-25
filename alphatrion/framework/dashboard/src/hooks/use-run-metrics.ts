import { useMemo } from 'react';
import type { Metric, RunMetrics } from '../types';
import { useExperiment } from './use-experiments';

/**
 * Hook to transform metrics from an experiment into a format suitable for Pareto analysis
 * Returns:
 * - runMetrics: Array of RunMetrics with the latest value for each metric per run
 * - availableMetrics: Array of unique metric keys across all runs
 */
export function useRunMetrics(experimentId: string) {
  const { data: experiment, ...rest } = useExperiment(experimentId);

  const { runMetrics, availableMetrics } = useMemo(() => {
    const metrics = experiment?.metrics || [];

    if (metrics.length === 0) {
      return { runMetrics: [], availableMetrics: [] };
    }

    // Group metrics by runId and key, keeping only the latest value
    const runMetricsMap = new Map<string, Map<string, number>>();
    const metricKeysSet = new Set<string>();

    // Sort metrics by createdAt to ensure we get the latest value
    const sortedMetrics = [...metrics].sort(
      (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );

    sortedMetrics.forEach((metric) => {
      if (!metric.key || metric.value === null) {
        return;
      }

      metricKeysSet.add(metric.key);

      if (!runMetricsMap.has(metric.runId)) {
        runMetricsMap.set(metric.runId, new Map());
      }

      // Overwrite with latest value (due to sorted order)
      runMetricsMap.get(metric.runId)!.set(metric.key, metric.value);
    });

    // Transform into RunMetrics array
    const runMetricsArray: RunMetrics[] = [];
    runMetricsMap.forEach((metricsMap, runId) => {
      const metricsObject: Record<string, number> = {};
      metricsMap.forEach((value, key) => {
        metricsObject[key] = value;
      });

      runMetricsArray.push({
        runId,
        metrics: metricsObject,
      });
    });

    return {
      runMetrics: runMetricsArray,
      availableMetrics: Array.from(metricKeysSet).sort(),
    };
  }, [experiment?.metrics]);

  return {
    ...rest,
    runMetrics,
    availableMetrics,
  };
}
