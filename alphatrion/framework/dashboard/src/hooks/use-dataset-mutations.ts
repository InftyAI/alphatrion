import { useMutation, useQueryClient } from '@tanstack/react-query';
import { graphqlMutation, mutations } from '../lib/graphql-client';

interface DeleteDatasetResponse {
  deleteDataset: boolean;
}

interface DeleteDatasetsResponse {
  deleteDatasets: number;
}

/**
 * Hook to delete a single dataset
 */
export function useDeleteDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (datasetId: string) => {
      const data = await graphqlMutation<DeleteDatasetResponse>(
        mutations.deleteDataset,
        { datasetId }
      );
      return data.deleteDataset;
    },
    onSuccess: () => {
      // Invalidate datasets queries to refetch the list
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['dataset'] });
    },
  });
}

/**
 * Hook to delete multiple datasets in batch
 */
export function useDeleteDatasets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (datasetIds: string[]) => {
      const data = await graphqlMutation<DeleteDatasetsResponse>(
        mutations.deleteDatasets,
        { datasetIds }
      );
      return data.deleteDatasets;
    },
    onSuccess: () => {
      // Invalidate datasets queries to refetch the list
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['dataset'] });
    },
  });
}
