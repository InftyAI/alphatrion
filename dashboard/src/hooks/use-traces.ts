import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Span } from '../types';

interface ListTracesResponse {
  traces: Span[];
}

/**
 * Hook to fetch all traces/spans for a run
 */
export function useTraces(runId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['traces', runId],
    queryFn: async () => {
      console.log('useTraces: Fetching traces for runId:', runId);
      const data = await graphqlQuery<ListTracesResponse>(
        queries.listTraces,
        { runId }
      );
      console.log('useTraces: Received data:', data);
      return data.traces;
    },
    enabled: enabled && !!runId,
    // Traces don't change after run completes, so cache for longer
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
