import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import { shouldPoll } from '../lib/query-client';
import type { Metric, GroupedMetrics } from '../types';
import { useExperiment } from './use-experiments';

interface ListMetricsResponse {
  experimentMetrics: Metric[];
}

/**
 * Hook to fetch all metrics for an experiment
 * Polls every 5s when parent experiment is RUNNING
 */
export function useMetrics(experimentId: string) {
  // Get experiment status to determine if we should poll
  const { data: experiment } = useExperiment(experimentId);

  return useQuery({
    queryKey: ['metrics', experimentId],
    queryFn: async () => {
      const data = await graphqlQuery<ListMetricsResponse>(
        queries.listMetrics,
        { experimentId }
      );
      return data.experimentMetrics;
    },
    // Poll when experiment is active
    refetchInterval: experiment
      ? shouldPoll([experiment.status])
      : false,
  });
}

/**
 * Hook to group metrics by key for easier chart rendering
 */
export function useGroupedMetrics(experimentId: string) {
  const { data: metrics, ...rest } = useMetrics(experimentId);

  const groupedMetrics: GroupedMetrics = {};

  if (metrics) {
    metrics.forEach((metric) => {
      const key = metric.key || 'unknown';
      if (!groupedMetrics[key]) {
        groupedMetrics[key] = [];
      }
      groupedMetrics[key].push(metric);
    });

    // Sort each group by createdAt
    Object.keys(groupedMetrics).forEach((key) => {
      groupedMetrics[key].sort((a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
      );
    });
  }

  return {
    ...rest,
    data: groupedMetrics,
    metricKeys: Object.keys(groupedMetrics),
  };
}
