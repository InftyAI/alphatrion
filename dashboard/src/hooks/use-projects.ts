import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Project } from '../types';

interface ListProjectsResponse {
  projects: Project[];
}

interface GetProjectResponse {
  project: Project | null;
}

/**
 * Hook to fetch all projects for a team
 * Projects are static data, so no polling is needed
 */
export function useProjects(
  teamId: string,
  options?: { page?: number; pageSize?: number; enabled?: boolean }
) {
  const { page = 0, pageSize = 100, enabled = true } = options || {};

  return useQuery({
    queryKey: ['projects', teamId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<ListProjectsResponse>(
        queries.listProjects,
        { teamId, page, pageSize }
      );
      return data.projects;
    },
    enabled: enabled && !!teamId,
    // Projects don't change frequently, cache for longer
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

/**
 * Hook to fetch a single project by ID
 */
export function useProject(projectId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const data = await graphqlQuery<GetProjectResponse>(
        queries.getProject,
        { id: projectId }
      );
      return data.project;
    },
    enabled: enabled && !!projectId,
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}
