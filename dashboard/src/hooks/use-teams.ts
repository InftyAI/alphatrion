import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Team } from '../types';

interface ListTeamsResponse {
  teams: Team[];
}

interface GetTeamResponse {
  team: Team | null;
}

/**
 * Hook to fetch all teams
 * Teams are static data, so no polling is needed
 */
export function useTeams(page = 0, pageSize = 100) {
  return useQuery({
    queryKey: ['teams', page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<ListTeamsResponse>(queries.listTeams);
      return data.teams;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch a single team by ID
 */
export function useTeam(teamId: string) {
  return useQuery({
    queryKey: ['team', teamId],
    queryFn: async () => {
      const data = await graphqlQuery<GetTeamResponse>(queries.getTeam, {
        id: teamId,
      });
      return data.team;
    },
    enabled: !!teamId,
    staleTime: 10 * 60 * 1000,
  });
}
