import { useMutation, useQueryClient } from '@tanstack/react-query';
import { graphqlMutation, mutations } from '../lib/graphql-client';

interface DeleteExperimentResponse {
  deleteExperiment: boolean;
}

interface DeleteExperimentsResponse {
  deleteExperiments: number;
}

/**
 * Hook to delete a single experiment
 */
export function useDeleteExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (experimentId: string) => {
      const data = await graphqlMutation<DeleteExperimentResponse>(
        mutations.deleteExperiment,
        { experimentId }
      );
      return data.deleteExperiment;
    },
    onSuccess: () => {
      // Invalidate experiments queries to refetch the list
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      queryClient.invalidateQueries({ queryKey: ['experiment'] });
    },
  });
}

/**
 * Hook to delete multiple experiments in batch
 */
export function useDeleteExperiments() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (experimentIds: string[]) => {
      const data = await graphqlMutation<DeleteExperimentsResponse>(
        mutations.deleteExperiments,
        { experimentIds }
      );
      return data.deleteExperiments;
    },
    onSuccess: () => {
      // Invalidate experiments queries to refetch the list
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      queryClient.invalidateQueries({ queryKey: ['experiment'] });
    },
  });
}
