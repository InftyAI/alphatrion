import { useQuery } from '@tanstack/react-query';
import {
  listRepositories,
  listTags,
  getManifest,
  getBlobAsText,
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
export function useTags(team: string, project: string) {
  return useQuery({
    queryKey: ['artifacts', 'tags', team, project],
    queryFn: () => listTags(team, project),
    enabled: Boolean(team && project),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch manifest for a specific tag
 */
export function useManifest(team: string, project: string, tag: string) {
  return useQuery({
    queryKey: ['artifacts', 'manifest', team, project, tag],
    queryFn: () => getManifest(team, project, tag),
    enabled: Boolean(team && project && tag),
    staleTime: 30 * 60 * 1000, // 30 minutes (immutable)
  });
}

/**
 * Hook to fetch blob content as text
 */
export function useBlobText(team: string, project: string, digest: string) {
  return useQuery({
    queryKey: ['artifacts', 'blob', team, project, digest],
    queryFn: () => getBlobAsText(team, project, digest),
    enabled: Boolean(team && project && digest),
    staleTime: 60 * 60 * 1000, // 1 hour (immutable)
  });
}
