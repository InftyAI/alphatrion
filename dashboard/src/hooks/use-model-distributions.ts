import { useQuery } from '@tanstack/react-query';
import { graphqlQuery } from '../lib/graphql-client';

export interface ModelDistribution {
  model: string;
  count: number;
}

interface GetModelDistributionsResponse {
  team: {
    modelDistributions: ModelDistribution[];
  };
}

const GET_MODEL_DISTRIBUTIONS = `
  query GetModelDistributions($teamId: ID!) {
    team(id: $teamId) {
      id
      modelDistributions {
        model
        count
      }
    }
  }
`;

export function useModelDistributions(teamId: string) {
  return useQuery<ModelDistribution[]>({
    queryKey: ['model-distributions', teamId],
    queryFn: async () => {
      if (!teamId) return [];
      const data = await graphqlQuery<GetModelDistributionsResponse>(
        GET_MODEL_DISTRIBUTIONS,
        { teamId }
      );
      return data.team?.modelDistributions || [];
    },
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
