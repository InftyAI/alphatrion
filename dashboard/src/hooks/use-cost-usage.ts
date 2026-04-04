import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';

export interface DailyCostUsage {
  date: string;
  totalCost: number;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  cacheReadInputTokens: number;
  cacheCreationInputTokens: number;
}

interface GetDailyCostUsageResponse {
  dailyCostUsage: DailyCostUsage[];
}

/**
 * Hook to fetch daily cost usage for a team
 * Only includes LLM calls (spans with alphatrion.cost.total_tokens)
 */
export function useDailyCostUsage(teamId: string, days = 30) {
  return useQuery({
    queryKey: ['dailyCostUsage', teamId, days],
    queryFn: async () => {
      const data = await graphqlQuery<GetDailyCostUsageResponse>(
        queries.getDailyCostUsage,
        { teamId, days }
      );
      return data.dailyCostUsage;
    },
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
