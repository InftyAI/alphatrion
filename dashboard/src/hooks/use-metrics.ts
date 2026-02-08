import { useMemo } from 'react';
import type { Metric, GroupedMetrics } from '../types';
import { useExperiment } from './use-experiments';

/**
 * Hook to get metrics from an experiment
 * Metrics are now part of the Experiment object
 */
export function useMetrics(experimentId: string) {
  const { data: experiment, ...rest } = useExperiment(experimentId);

  return {
    ...rest,
    data: experiment?.metrics || [],
  };
}

/**
 * Hook to group metrics by key for easier chart rendering
 */
export function useGroupedMetrics(experimentId: string) {
  const { data: experiment, ...rest } = useExperiment(experimentId);

  const groupedMetrics: GroupedMetrics = useMemo(() => {
    const grouped: GroupedMetrics = {};
    const metrics = experiment?.metrics || [];

    metrics.forEach((metric) => {
      const key = metric.key || 'unknown';
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(metric);
    });

    // Sort each group by createdAt
    Object.keys(grouped).forEach((key) => {
      grouped[key].sort((a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
      );
    });

    return grouped;
  }, [experiment?.metrics]);

  return {
    ...rest,
    data: groupedMetrics,
    metricKeys: Object.keys(groupedMetrics),
  };
}
