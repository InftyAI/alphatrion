import { useQuery } from '@tanstack/react-query';
import {
  listRepositories,
  listTags,
  getArtifactContent,
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

/**
 * Hook to fetch artifact content with caching
 * Artifacts are immutable, so we cache them indefinitely
 */
export function useArtifactContent(
  teamId: string,
  projectId: string,
  tag: string,
  repoType?: 'execution' | 'checkpoint',
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['artifacts', 'content', teamId, projectId, tag, repoType],
    queryFn: () => getArtifactContent(teamId, projectId, tag, repoType),
    enabled: Boolean(enabled && teamId && projectId && tag),
    // Artifacts are immutable - cache indefinitely
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes after last use (renamed from cacheTime in React Query v5)
    retry: 1, // Only retry once on failure
  });
}
