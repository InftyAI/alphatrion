import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import { shouldPollRuns } from '../lib/query-client';
import type { Run } from '../types';

interface ListRunsResponse {
  runs: Run[];
}

interface GetRunResponse {
  run: Run | null;
}

/**
 * Hook to fetch all runs for an experiment
 * Polls every 3s when any run is RUNNING or PENDING
 */
export function useRuns(
  experimentId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 100, enabled = true } = options || {};

  return useQuery({
    queryKey: ['runs', experimentId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<ListRunsResponse>(
        queries.listRuns,
        { experimentId, page, pageSize }
      );
      return data.runs;
    },
    enabled: enabled && !!experimentId,
    // Poll when any run is active
    refetchInterval: (query) => {
      const runs = query.state.data;
      if (!runs) return false;

      const statuses = runs.map(run => run.status);
      return shouldPollRuns(statuses);
    },
  });
}

/**
 * Hook to fetch a single run by ID
 */
export function useRun(runId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['run', runId],
    queryFn: async () => {
      const data = await graphqlQuery<GetRunResponse>(
        queries.getRun,
        { id: runId }
      );
      return data.run;
    },
    enabled: enabled && !!runId,
    // Poll when run is active
    refetchInterval: (query) => {
      const run = query.state.data;
      if (!run) return false;

      return shouldPollRuns([run.status]);
    },
  });
}
