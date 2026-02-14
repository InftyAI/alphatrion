import { useQuery } from '@tanstack/react-query';
import {
  listRepositories,
  listTags,
} from '../lib/artifact-client';

/**
 * Hook to fetch all repositories from ORAS registry
 * No polling needed (artifacts are immutable)
 */
export function useRepositories() {
  return useQuery({
    queryKey: ['artifacts', 'repositories'],
    queryFn: listRepositories,
    // Cache aggressively since repositories don't change often
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

/**
 * Hook to fetch tags for a specific repository
 */
export function useTags(
  teamId: string,
  projectId: string,
  repoType?: 'execution' | 'checkpoint'
) {
  return useQuery({
    queryKey: ['artifacts', 'tags', teamId, projectId, repoType],
    queryFn: () => listTags(teamId, projectId, repoType),
    enabled: Boolean(teamId && projectId),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
