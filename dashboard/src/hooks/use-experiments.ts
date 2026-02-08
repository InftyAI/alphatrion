import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import { shouldPoll } from '../lib/query-client';
import type { Experiment } from '../types';

interface ListExperimentsResponse {
  experiments: Experiment[];
}

interface GetExperimentResponse {
  experiment: Experiment | null;
}

/**
 * Hook to fetch all experiments for a project
 * Polls every 5s when any experiment is RUNNING or PENDING
 */
export function useExperiments(
  projectId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 100, enabled = true } = options || {};

  return useQuery({
    queryKey: ['experiments', projectId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<ListExperimentsResponse>(
        queries.listExperiments,
        { projectId, page, pageSize }
      );
      return data.experiments;
    },
    enabled: enabled && !!projectId,
    // Poll when any experiment is active
    refetchInterval: (query) => {
      const experiments = query.state.data;
      if (!experiments) return false;

      const statuses = experiments.map(exp => exp.status);
      return shouldPoll(statuses);
    },
  });
}

/**
 * Hook to fetch a single experiment by ID
 * Polls every 5s when experiment is RUNNING or PENDING
 */
export function useExperiment(experimentId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['experiment', experimentId],
    queryFn: async () => {
      const data = await graphqlQuery<GetExperimentResponse>(
        queries.getExperiment,
        { id: experimentId }
      );
      return data.experiment;
    },
    enabled: enabled && !!experimentId,
    // Poll when experiment is active
    refetchInterval: (query) => {
      const experiment = query.state.data;
      if (!experiment) return false;

      return shouldPoll([experiment.status]);
    },
  });
}

/**
 * Hook to fetch multiple experiments by IDs (for comparison)
 */
export function useExperimentsByIds(experimentIds: string[]) {
  return useQuery({
    queryKey: ['experiments', 'by-ids', experimentIds],
    queryFn: async () => {
      const experiments = await Promise.all(
        experimentIds.map(async (id) => {
          const data = await graphqlQuery<GetExperimentResponse>(
            queries.getExperiment,
            { id }
          );
          return data.experiment;
        })
      );
      return experiments.filter((exp): exp is Experiment => exp !== null);
    },
    enabled: experimentIds.length > 0,
    // Poll when any experiment is active
    refetchInterval: (query) => {
      const experiments = query.state.data;
      if (!experiments) return false;

      const statuses = experiments.map(exp => exp.status);
      return shouldPoll(statuses);
    },
  });
}
