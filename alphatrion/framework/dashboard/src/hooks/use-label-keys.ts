import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';

interface GetTeamWithLabelKeysResponse {
  team: {
    id: string;
    labelKeys: string[];
  };
}

/**
 * Hook to fetch label keys for a team
 */
export function useLabelKeys(teamId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['labelKeys', teamId],
    queryFn: async () => {
      const data = await graphqlQuery<GetTeamWithLabelKeysResponse>(
        queries.getTeamWithLabelKeys,
        { id: teamId }
      );
      return data.team.labelKeys;
    },
    enabled: enabled && !!teamId,
    staleTime: 10 * 60 * 1000, // 10 minutes - label keys don't change often
  });
}
