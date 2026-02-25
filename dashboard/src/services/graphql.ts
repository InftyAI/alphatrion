import { graphqlQuery } from "../lib/graphql-client";
import type {
  ContentSnapshot,
  ContentSnapshotSummary,
  RepoFileTree,
  RepoFileContent,
} from "../types";

/**
 * Fetch a single content snapshot by ID with full content
 */
export async function fetchContentSnapshot(id: string): Promise<ContentSnapshot> {
  const query = `
    query GetContentSnapshot($id: ID!) {
      contentSnapshot(id: $id) {
        id
        projectId
        experimentId
        runId
        contentUid
        contentText
        parentUid
        coParentUids
        fitness
        evaluation
        metainfo
        language
        createdAt
      }
    }
  `;
  const data = await graphqlQuery<{ contentSnapshot: ContentSnapshot }>(query, { id });
  return data.contentSnapshot;
}

/**
 * Fetch content snapshots summary (lightweight, no contentText) for an experiment
 */
export async function fetchContentSnapshotsSummary(params: {
  experimentId: string;
}): Promise<ContentSnapshotSummary[]> {
  const query = `
    query GetContentSnapshotsSummary($experimentId: ID!) {
      contentSnapshotsSummary(experimentId: $experimentId) {
        id
        projectId
        experimentId
        runId
        contentUid
        parentUid
        coParentUids
        fitness
        language
        metainfo
        createdAt
      }
    }
  `;
  const data = await graphqlQuery<{ contentSnapshotsSummary: ContentSnapshotSummary[] }>(
    query,
    { experimentId: params.experimentId }
  );
  return data.contentSnapshotsSummary;
}

/**
 * Fetch content lineage for a given content UID
 */
export async function fetchContentLineage(params: {
  experimentId: string;
  contentUid: string;
}): Promise<ContentSnapshotSummary[]> {
  const query = `
    query GetContentLineage($experimentId: ID!, $contentUid: String!) {
      contentLineage(experimentId: $experimentId, contentUid: $contentUid) {
        id
        projectId
        experimentId
        runId
        contentUid
        parentUid
        coParentUids
        fitness
        language
        metainfo
        createdAt
      }
    }
  `;
  const data = await graphqlQuery<{ contentLineage: ContentSnapshotSummary[] }>(query, params);
  return data.contentLineage;
}

/**
 * Fetch repository file tree for an experiment
 */
export async function fetchRepoFileTree(experimentId: string): Promise<RepoFileTree> {
  const query = `
    query GetRepoFileTree($experimentId: ID!) {
      repoFileTree(experimentId: $experimentId) {
        exists
        root {
          name
          path
          isDir
          children {
            name
            path
            isDir
          }
        }
        error
      }
    }
  `;
  const data = await graphqlQuery<{ repoFileTree: RepoFileTree }>(query, { experimentId });
  return data.repoFileTree;
}

/**
 * Fetch repository file content for a specific file in an experiment
 */
export async function fetchRepoFileContent(
  experimentId: string,
  path: string
): Promise<RepoFileContent> {
  const query = `
    query GetRepoFileContent($experimentId: ID!, $path: String!) {
      repoFileContent(experimentId: $experimentId, path: $path) {
        path
        content
        error
      }
    }
  `;
  const data = await graphqlQuery<{ repoFileContent: RepoFileContent }>(query, {
    experimentId,
    path,
  });
  return data.repoFileContent;
}

/**
 * Fetch metrics by key for an experiment
 */
export async function fetchMetricsByKey(
  experimentId: string,
  key: string
): Promise<Array<{ timestamp: string; value: number }>> {
  // Stub implementation - return empty array for now
  console.warn("fetchMetricsByKey not yet implemented");
  return [];
}

/**
 * Sync files to pod (for terminal integration)
 */
export async function syncFilesToPod(params: {
  experimentId: string;
  files: Array<{ path: string; content: string }>;
}): Promise<boolean> {
  // Stub implementation
  console.warn("syncFilesToPod not yet implemented");
  return false;
}

// Stub functions for hooks - TODO: Implement these properly
export async function fetchProjects(): Promise<any[]> {
  console.warn("fetchProjects not yet implemented");
  return [];
}

export async function fetchExperiments(): Promise<any[]> {
  console.warn("fetchExperiments not yet implemented");
  return [];
}

export async function fetchExperiment(id: string): Promise<any> {
  console.warn("fetchExperiment not yet implemented");
  return null;
}

export async function fetchTrials(): Promise<any[]> {
  console.warn("fetchTrials not yet implemented - using experiment-based architecture");
  return [];
}

export async function fetchTrial(id: string): Promise<any> {
  console.warn("fetchTrial not yet implemented - using experiment-based architecture");
  return null;
}

export async function fetchRuns(experimentId?: string): Promise<any[]> {
  console.warn("fetchRuns not yet implemented");
  return [];
}

export async function fetchRun(id: string): Promise<any> {
  console.warn("fetchRun not yet implemented");
  return null;
}

export async function fetchTrialMetrics(trialId: string): Promise<any[]> {
  console.warn("fetchTrialMetrics not yet implemented - using experiment-based architecture");
  return [];
}

export async function fetchMetricKeys(experimentId: string): Promise<string[]> {
  console.warn("fetchMetricKeys not yet implemented");
  return [];
}

export async function analyzeTrialCode(params: any): Promise<any> {
  console.warn("analyzeTrialCode not yet implemented");
  return null;
}
