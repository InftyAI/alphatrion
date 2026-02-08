import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import { subMonths } from 'date-fns';

export interface TeamExperiment {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  name: string;
  status: string;
  createdAt: string;
}

interface GetTeamWithExperimentsResponse {
  team: {
    id: string;
    name: string;
    listExpsByTimeframe: TeamExperiment[];
  };
}

export function useTeamExperiments(
  teamId: string,
  options?: { enabled?: boolean }
) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['teamExperimentsByTimeframe', teamId],
    queryFn: async () => {
      // Get experiments from the last 3 months
      const endTime = new Date();
      const startTime = subMonths(endTime, 3);

      const data = await graphqlQuery<GetTeamWithExperimentsResponse>(
        queries.getTeamWithExperiments,
        {
          id: teamId,
          startTime: startTime.toISOString(),
          endTime: endTime.toISOString(),
        }
      );
      return data.team.listExpsByTimeframe;
    },
    enabled: enabled && !!teamId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
