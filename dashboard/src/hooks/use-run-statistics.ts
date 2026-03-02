import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Status } from '../types';

interface RunStatus {
  status: Status;
}

interface RunDuration {
  duration: number;
  status: Status;
}

interface ListRunStatusesResponse {
  runs: RunStatus[];
}

interface ListRunDurationsResponse {
  runs: RunDuration[];
}

/**
 * Hook to fetch run statuses for experiment statistics
 * Only fetches status field for optimal performance
 */
export function useRunStatistics(experimentId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['run-statistics', experimentId],
    queryFn: async () => {
      const data = await graphqlQuery<ListRunStatusesResponse>(
        queries.listRunStatuses,
        { experimentId }
      );
      return data.runs;
    },
    enabled: enabled && !!experimentId,
    staleTime: 30000, // Cache for 30 seconds
  });
}

/**
 * Hook to fetch run durations for experiment statistics
 * Fetches duration and status fields for calculating average iteration time
 */
export function useRunDurations(experimentId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['run-durations', experimentId],
    queryFn: async () => {
      const data = await graphqlQuery<ListRunDurationsResponse>(
        queries.listRunDurations,
        { experimentId }
      );
      return data.runs;
    },
    enabled: enabled && !!experimentId,
    staleTime: 30000, // Cache for 30 seconds
  });
}
