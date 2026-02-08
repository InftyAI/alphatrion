import axios from 'axios';
import type { ArtifactManifest } from '../types';

/**
 * Artifact client for ORAS registry access via backend proxy
 *
 * All requests go through backend proxy endpoints at /api/artifacts/*
 * to avoid CORS issues and handle authentication.
 */

const ARTIFACT_API_BASE = import.meta.env.VITE_API_URL || '/api/artifacts';

export interface RepositoryCatalog {
  repositories: string[];
}

export interface TagList {
  name: string;
  tags: string[];
}

/**
 * List all repositories in the ORAS registry
 */
export async function listRepositories(): Promise<string[]> {
  try {
    const response = await axios.get<RepositoryCatalog>(
      `${ARTIFACT_API_BASE}/repositories`
    );
    return response.data.repositories || [];
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to list repositories: ${error.message}`);
    }
    throw error;
  }
}

/**
 * List tags for a specific repository
 * Repository path format: team/project
 */
export async function listTags(team: string, project: string): Promise<string[]> {
  try {
    const response = await axios.get<TagList>(
      `${ARTIFACT_API_BASE}/repositories/${team}/${project}/tags`
    );
    return response.data.tags || [];
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to list tags for ${team}/${project}: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Get manifest for a specific tag
 */
export async function getManifest(
  team: string,
  project: string,
  tag: string
): Promise<ArtifactManifest> {
  try {
    const response = await axios.get<ArtifactManifest>(
      `${ARTIFACT_API_BASE}/repositories/${team}/${project}/manifests/${tag}`
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to get manifest for ${team}/${project}:${tag}: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Get blob content from registry
 */
export async function getBlob(
  team: string,
  project: string,
  digest: string
): Promise<Blob> {
  try {
    const response = await axios.get(
      `${ARTIFACT_API_BASE}/repositories/${team}/${project}/blobs/${digest}`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to get blob ${digest}: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Get blob as text (for preview)
 */
export async function getBlobAsText(
  team: string,
  project: string,
  digest: string
): Promise<string> {
  try {
    const blob = await getBlob(team, project, digest);
    return await blob.text();
  } catch (error) {
    throw new Error(`Failed to read blob as text: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get blob as JSON
 */
export async function getBlobAsJSON<T>(
  team: string,
  project: string,
  digest: string
): Promise<T> {
  try {
    const text = await getBlobAsText(team, project, digest);
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`Failed to parse blob as JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Parse repository name from full path
 * Expected format: team/project
 */
export function parseRepositoryPath(fullPath: string): { team: string; project: string } | null {
  const parts = fullPath.split('/');
  if (parts.length !== 2) {
    return null;
  }
  return {
    team: parts[0],
    project: parts[1],
  };
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

/**
 * Check if media type is previewable as text
 */
export function isTextPreviewable(mediaType: string): boolean {
  const textTypes = [
    'text/',
    'application/json',
    'application/xml',
    'application/yaml',
    'application/x-yaml',
  ];
  return textTypes.some(type => mediaType.startsWith(type));
}

/**
 * Check if media type is an image
 */
export function isImagePreviewable(mediaType: string): boolean {
  return mediaType.startsWith('image/');
}
