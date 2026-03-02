import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Status } from '../types';

interface RunStatus {
  status: Status;
}

interface ListRunStatusesResponse {
  runs: RunStatus[];
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
