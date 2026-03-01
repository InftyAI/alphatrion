import axios from 'axios';

/**
 * GraphQL client for AlphaTrion backend
 *
 * The backend provides a read-only GraphQL API at /graphql
 * with queries for teams, experiments, runs, and metrics.
 *
 * No subscriptions or mutations are currently supported.
 */

// Use relative URL to work with proxy in development
const GRAPHQL_ENDPOINT = import.meta.env.VITE_GRAPHQL_URL || '/graphql';

export interface GraphQLResponse<T> {
  data?: T;
  errors?: Array<{
    message: string;
    locations?: Array<{ line: number; column: number }>;
    path?: string[];
  }>;
}

/**
 * Execute a GraphQL query
 */
export async function graphqlQuery<T>(
  query: string,
  variables?: Record<string, unknown>
): Promise<T> {
  try {
    const response = await axios.post<GraphQLResponse<T>>(
      GRAPHQL_ENDPOINT,
      {
        query,
        variables,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (response.data.errors) {
      throw new Error(
        response.data.errors.map(e => e.message).join(', ')
      );
    }

    if (!response.data.data) {
      throw new Error('No data returned from GraphQL query');
    }

    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        `GraphQL request failed: ${error.message}`
      );
    }
    throw error;
  }
}

// GraphQL query templates
export const queries = {
  listTeams: `
    query ListTeams($userId: ID!) {
      teams(userId: $userId) {
        id
        name
        description
        meta
        createdAt
        updatedAt
      }
    }
  `,

  getUser: `
    query GetUser($id: ID!) {
      user(id: $id) {
        id
        username
        email
        avatarUrl
        meta
        createdAt
        updatedAt
      }
    }
  `,

  getTeam: `
    query GetTeam($id: ID!) {
      team(id: $id) {
        id
        name
        description
        meta
        createdAt
        updatedAt
        totalExperiments
        totalRuns
        aggregatedTokens {
          totalTokens
          inputTokens
          outputTokens
        }
      }
    }
  `,

  getTeamWithExperiments: `
    query GetTeamWithExperiments($id: ID!, $startTime: DateTime!, $endTime: DateTime!) {
      team(id: $id) {
        id
        name
        expsByTimeframe(startTime: $startTime, endTime: $endTime) {
          id
          teamId
          userId
          name
          status
          createdAt
        }
      }
    }
  `,

  getTeamWithLabelKeys: `
    query GetTeamWithLabelKeys($id: ID!) {
      team(id: $id) {
        id
        labelKeys
      }
    }
  `,

  listExperiments: `
    query ListExperiments($teamId: ID!, $labelName: String, $labelValue: String, $page: Int, $pageSize: Int) {
      experiments(teamId: $teamId, labelName: $labelName, labelValue: $labelValue, page: $page, pageSize: $pageSize) {
        id
        teamId
        userId
        name
        description
        kind
        meta
        params
        labels {
          name
          value
        }
        duration
        status
        createdAt
        updatedAt
      }
    }
  `,

  getExperiment: `
    query GetExperiment($id: ID!) {
      experiment(id: $id) {
        id
        teamId
        userId
        name
        description
        kind
        meta
        params
        labels {
          name
          value
        }
        duration
        status
        createdAt
        updatedAt
        aggregatedTokens {
          totalTokens
          inputTokens
          outputTokens
        }
        metrics {
          id
          key
          value
          teamId
          experimentId
          runId
          createdAt
        }
      }
    }
  `,

  listRuns: `
    query ListRuns($experimentId: ID!, $page: Int, $pageSize: Int) {
      runs(experimentId: $experimentId, page: $page, pageSize: $pageSize) {
        id
        teamId
        userId
        experimentId
        meta
        status
        createdAt
      }
    }
  `,

  getRun: `
    query GetRun($id: ID!) {
      run(id: $id) {
        id
        teamId
        userId
        experimentId
        meta
        status
        createdAt
        aggregatedTokens {
          totalTokens
          inputTokens
          outputTokens
        }
        metrics {
          id
          key
          value
          teamId
          experimentId
          runId
          createdAt
        }
        spans {
          timestamp
          traceId
          spanId
          parentSpanId
          spanName
          spanKind
          semanticKind
          serviceName
          duration
          statusCode
          statusMessage
          teamId
          runId
          experimentId
          spanAttributes
          resourceAttributes
          events {
            timestamp
            name
            attributes
          }
          links {
            traceId
            spanId
            attributes
          }
        }
      }
    }
  `,

  // Artifact queries
  listArtifactRepositories: `
    query ListArtifactRepositories {
      artifactRepos {
        name
      }
    }
  `,

  listArtifactTags: `
    query ListArtifactTags($team_id: ID!, $repo_name: String!) {
      artifactTags(teamId: $team_id, repoName: $repo_name) {
        name
      }
    }
  `,

  getArtifactContent: `
    query GetArtifactContent($team_id: ID!, $tag: String!, $repo_name: String!) {
      artifactContent(teamId: $team_id, tag: $tag, repoName: $repo_name) {
        filename
        content
        contentType
      }
    }
  `,

  // Trace queries
  listTraces: `
    query ListTraces($runId: ID!) {
      traces(runId: $runId) {
        timestamp
        traceId
        spanId
        parentSpanId
        spanName
        spanKind
        semanticKind
        serviceName
        duration
        statusCode
        statusMessage
        teamId
        runId
        experimentId
        spanAttributes
        resourceAttributes
        events {
          timestamp
          name
          attributes
        }
        links {
          traceId
          spanId
          attributes
        }
      }
    }
  `,

  getDailyTokenUsage: `
    query GetDailyTokenUsage($teamId: ID!, $days: Int = 30) {
      dailyTokenUsage(teamId: $teamId, days: $days) {
        date
        totalTokens
        inputTokens
        outputTokens
      }
    }
  `,

  // Content Snapshot queries (for IDE component)
  listContentSnapshots: `
    query ListContentSnapshots($experimentId: ID!, $page: Int, $pageSize: Int) {
      contentSnapshots(experimentId: $experimentId, page: $page, pageSize: $pageSize) {
        id
        teamId
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
  `,

  listContentSnapshotsSummary: `
    query ListContentSnapshotsSummary($experimentId: ID!, $page: Int, $pageSize: Int) {
      contentSnapshotsSummary(experimentId: $experimentId, page: $page, pageSize: $pageSize) {
        id
        teamId
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
  `,

  getContentSnapshot: `
    query GetContentSnapshot($id: ID!) {
      contentSnapshot(id: $id) {
        id
        teamId
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
  `,

  getContentLineage: `
    query GetContentLineage($experimentId: ID!, $contentUid: String!) {
      contentLineage(experimentId: $experimentId, contentUid: $contentUid) {
        id
        teamId
        experimentId
        runId
        contentUid
        parentUid
        coParentUids
        fitness
        evaluation
        metainfo
        language
        createdAt
      }
    }
  `,

  // Repository File Browser queries (for IDE component)
  getRepoFileTree: `
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
            children {
              name
              path
              isDir
              children {
                name
                path
                isDir
                children {
                  name
                  path
                  isDir
                  children {
                    name
                    path
                    isDir
                    children {
                      name
                      path
                      isDir
                      children {
                        name
                        path
                        isDir
                      }
                    }
                  }
                }
              }
            }
          }
        }
        error
      }
    }
  `,

  getRepoFileContent: `
    query GetRepoFileContent($experimentId: ID!, $filePath: String!) {
      repoFileContent(experimentId: $experimentId, filePath: $filePath) {
        path
        content
        language
        error
      }
    }
  `,

  // Metrics queries for experiment (for IDE component)
  listMetricKeys: `
    query ListMetricKeys($experimentId: ID!) {
      metricKeys(experimentId: $experimentId)
    }
  `,

  listMetricsByKey: `
    query ListMetricsByKey($experimentId: ID!, $key: String!, $maxPoints: Int) {
      metricsByKey(experimentId: $experimentId, key: $key, maxPoints: $maxPoints) {
        id
        key
        value
        teamId
        experimentId
        runId
        createdAt
      }
    }
  `,

};

// Import types for helper functions
import type {
  Metric,
  ContentSnapshot,
  ContentSnapshotSummary,
  ContentSnapshotsQueryParams,
  ContentLineageQueryParams,
  RepoFileTree,
  RepoFileContent,
} from '../types';

// Helper functions for IDE component hooks

export async function fetchContentSnapshotsSummary(
  params: ContentSnapshotsQueryParams
): Promise<ContentSnapshotSummary[]> {
  const data = await graphqlQuery<{ contentSnapshotsSummary: ContentSnapshotSummary[] }>(
    queries.listContentSnapshotsSummary,
    {
      experimentId: params.experimentId,
      page: params.page ?? 0,
      pageSize: params.pageSize ?? 2000,
    }
  );
  return data.contentSnapshotsSummary;
}

export async function fetchContentSnapshot(id: string): Promise<ContentSnapshot | null> {
  const data = await graphqlQuery<{ contentSnapshot: ContentSnapshot | null }>(
    queries.getContentSnapshot,
    { id }
  );
  return data.contentSnapshot;
}

export async function fetchContentLineage(
  params: ContentLineageQueryParams
): Promise<ContentSnapshot[]> {
  const data = await graphqlQuery<{ contentLineage: ContentSnapshot[] }>(
    queries.getContentLineage,
    {
      experimentId: params.experimentId,
      contentUid: params.contentUid,
    }
  );
  return data.contentLineage;
}

export async function fetchRepoFileTree(experimentId: string): Promise<RepoFileTree> {
  const data = await graphqlQuery<{ repoFileTree: RepoFileTree }>(
    queries.getRepoFileTree,
    { experimentId }
  );
  return data.repoFileTree;
}

export async function fetchRepoFileContent(
  experimentId: string,
  filePath: string
): Promise<RepoFileContent> {
  const data = await graphqlQuery<{ repoFileContent: RepoFileContent }>(
    queries.getRepoFileContent,
    { experimentId, filePath }
  );
  return data.repoFileContent;
}

export async function fetchMetricKeys(experimentId: string): Promise<string[]> {
  const data = await graphqlQuery<{ metricKeys: string[] }>(
    queries.listMetricKeys,
    { experimentId }
  );
  return data.metricKeys;
}

export async function fetchMetricsByKey(
  experimentId: string,
  key: string,
  maxPoints: number = 1000
): Promise<Metric[]> {
  const data = await graphqlQuery<{ metricsByKey: Metric[] }>(
    queries.listMetricsByKey,
    { experimentId, key, maxPoints }
  );
  return data.metricsByKey;
}
