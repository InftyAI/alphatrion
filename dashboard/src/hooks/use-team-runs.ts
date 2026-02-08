import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';

export interface TeamRun {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  experimentId: string;
  meta: Record<string, unknown>;
  status: string;
  createdAt: string;
}

interface GetTeamRunsResponse {
  teamRuns: TeamRun[];
}

export function useTeamRuns(
  teamId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 1000, enabled = true } = options || {};

  return useQuery({
    queryKey: ['teamRuns', teamId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<GetTeamRunsResponse>(
        queries.listTeamRuns,
        { teamId, page, pageSize }
      );
      return data.teamRuns;
    },
    enabled: enabled && !!teamId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
