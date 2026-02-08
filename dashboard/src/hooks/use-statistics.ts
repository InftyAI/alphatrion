import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';

export interface Statistics {
  totalProjects: number;
  totalExperiments: number;
  totalRuns: number;
}

interface GetStatisticsResponse {
  statistics: Statistics;
}

/**
 * Hook to fetch statistics for a team
 */
export function useStatistics(teamId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['statistics', teamId],
    queryFn: async () => {
      const data = await graphqlQuery<GetStatisticsResponse>(
        queries.getStatistics,
        { teamId }
      );
      return data.statistics;
    },
    enabled: enabled && !!teamId,
    staleTime: 60 * 60 * 1000, // 1 hour - statistics don't change frequently
  });
}
