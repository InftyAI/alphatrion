import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Dataset } from '../types';

interface ListDatasetsResponse {
  datasets: Dataset[];
}

interface GetDatasetResponse {
  dataset: Dataset | null;
}

/**
 * Hook to fetch all datasets for a team
 */
export function useDatasets(
  teamId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 20, enabled = true } = options || {};

  return useQuery({
    queryKey: ['datasets', teamId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<ListDatasetsResponse>(
        queries.listDatasets,
        { teamId, page, pageSize }
      );
      return data.datasets;
    },
    enabled: enabled && !!teamId,
  });
}

/**
 * Hook to fetch a single dataset by ID
 */
export function useDataset(datasetId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: async () => {
      const data = await graphqlQuery<GetDatasetResponse>(
        queries.getDataset,
        { id: datasetId }
      );
      return data.dataset;
    },
    enabled: enabled && !!datasetId,
  });
}

/**
 * Hook to fetch datasets by experiment ID
 */
export function useDatasetsByExperiment(
  teamId: string,
  experimentId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 20, enabled = true } = options || {};

  return useQuery({
    queryKey: ['datasets', 'by-experiment', teamId, experimentId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<{ datasetsByExperiment: Dataset[] }>(
        queries.listDatasetsByExperiment,
        { teamId, experimentId, page, pageSize }
      );
      return data.datasetsByExperiment;
    },
    enabled: enabled && !!teamId && !!experimentId,
  });
}
