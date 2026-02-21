import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';

export interface DailyTokenUsage {
  date: string;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
}

interface GetDailyTokenUsageResponse {
  dailyTokenUsage: DailyTokenUsage[];
}

/**
 * Hook to fetch daily token usage for a team
 * Only includes LLM calls (spans with llm.usage.total_tokens)
 */
export function useDailyTokenUsage(teamId: string, days = 30) {
  return useQuery({
    queryKey: ['dailyTokenUsage', teamId, days],
    queryFn: async () => {
      const data = await graphqlQuery<GetDailyTokenUsageResponse>(
        queries.getDailyTokenUsage,
        { teamId, days }
      );
      return data.dailyTokenUsage;
    },
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
