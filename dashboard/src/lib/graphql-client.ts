import axios from 'axios';

/**
 * GraphQL client for AlphaTrion backend
 *
 * The backend provides a GraphQL API at /graphql
 * with queries and mutations for teams, experiments, runs, and metrics.
 */

// Use runtime config (Kubernetes) > build-time env (Docker) > localhost dev
const getApiBaseUrl = () => {
  // @ts-ignore - window.ENV is injected at runtime by entrypoint.sh
  if (typeof window !== 'undefined' && window.ENV?.VITE_API_URL) {
    // @ts-ignore
    return window.ENV.VITE_API_URL;
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();
const GRAPHQL_ENDPOINT = `${API_BASE_URL}/graphql`;

// Setup axios interceptor to handle auth errors globally
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    // Check for 401 Unauthorized or 403 Forbidden
    if (error.response?.status === 401 || error.response?.status === 403) {
      // Clear stored auth data
      localStorage.removeItem('alphatrion_token');
      localStorage.removeItem('alphatrion_org_id');
      localStorage.removeItem('alphatrion_user_id');

      // Redirect to login page
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface GraphQLResponse<T> {
  data?: T;
  errors?: Array<{
    message: string;
    locations?: Array<{ line: number; column: number }>;
    path?: string[];
  }>;
}

/**
 * Get authentication headers from localStorage
 * Supports both JWT-based and direct header authentication
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Try JWT token first
  const token = localStorage.getItem('alphatrion_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    return headers;
  }

  // Fallback to direct headers for backwards compatibility
  const orgId = localStorage.getItem('alphatrion_org_id');
  const userId = localStorage.getItem('alphatrion_user_id');

  if (orgId) headers['x-org-id'] = orgId;
  if (userId) headers['x-user-id'] = userId;

  return headers;
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
        headers: getAuthHeaders(),
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
    // Auth errors are handled by axios interceptor
    if (axios.isAxiosError(error)) {
      throw new Error(
        `GraphQL request failed: ${error.message}`
      );
    }
    throw error;
  }
}

/**
 * Execute a GraphQL mutation
 */
export async function graphqlMutation<T>(
  mutation: string,
  variables?: Record<string, unknown>
): Promise<T> {
  // Mutations use the same endpoint and logic as queries
  return graphqlQuery<T>(mutation, variables);
}

// GraphQL query templates
export const queries = {
  listTeams: `
    query ListTeams {
      teams {
        id
        orgId
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
        orgId
        name
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
        orgId
        name
        description
        meta
        createdAt
        updatedAt
        totalExperiments
        totalRuns
        totalDatasets
        totalAgents
        totalSessions
        aggregatedUsage {
          totalTokens
          inputTokens
          outputTokens
          cacheReadInputTokens
          cacheCreationInputTokens
          totalCost
        }
      }
    }
  `,

  getOrganization: `
    query GetOrganization($id: ID!) {
      organization(id: $id) {
        id
        name
        description
        meta
        createdAt
        updatedAt
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
    query ListExperiments($teamId: ID!, $labelName: String, $labelValue: String, $tag: String, $page: Int, $pageSize: Int) {
      experiments(teamId: $teamId, labelName: $labelName, labelValue: $labelValue, tag: $tag, page: $page, pageSize: $pageSize) {
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
        tags
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
        tags
        duration
        status
        createdAt
        updatedAt
        aggregatedUsage {
          totalTokens
          inputTokens
          outputTokens
          cacheReadInputTokens
          cacheCreationInputTokens
          totalCost
        }
        traceStats {
          totalSpans
          successSpans
          errorSpans
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
        duration
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
        duration
        status
        createdAt
        aggregatedUsage {
          totalTokens
          inputTokens
          outputTokens
          cacheReadInputTokens
          cacheCreationInputTokens
          totalCost
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

  listArtifactFiles: `
    query ListArtifactFiles($team_id: ID!, $tag: String!, $repo_name: String!) {
      artifactFiles(teamId: $team_id, tag: $tag, repoName: $repo_name) {
        filename
        size
        contentType
      }
    }
  `,

  getArtifactContent: `
    query GetArtifactContent($team_id: ID!, $tag: String!, $repo_name: String!, $filename: String) {
      artifactContent(teamId: $team_id, tag: $tag, repoName: $repo_name, filename: $filename) {
        filename
        content
        contentType
      }
    }
  `,

  // Span queries
  listTraces: `
    query ListSpans($runId: ID!) {
      spansByRunId(runId: $runId) {
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

  getDailyCostUsage: `
    query GetDailyCostUsage($teamId: ID!, $days: Int = 30) {
      dailyCostUsage(teamId: $teamId, days: $days) {
        date
        totalCost
        totalTokens
        inputTokens
        outputTokens
        cacheReadInputTokens
        cacheCreationInputTokens
      }
    }
  `,

  listDatasets: `
    query ListDatasets($teamId: ID!, $page: Int, $pageSize: Int) {
      datasets(teamId: $teamId, page: $page, pageSize: $pageSize) {
        id
        name
        description
        path
        meta
        teamId
        experimentId
        runId
        userId
        createdAt
        updatedAt
      }
    }
  `,

  getDataset: `
    query GetDataset($id: ID!) {
      dataset(id: $id) {
        id
        name
        description
        path
        meta
        teamId
        experimentId
        runId
        userId
        createdAt
        updatedAt
      }
    }
  `,

  listDatasetsByExperiment: `
    query ListDatasetsByExperiment($teamId: ID!, $experimentId: ID!, $page: Int, $pageSize: Int) {
      datasetsByExperiment(teamId: $teamId, experimentId: $experimentId, page: $page, pageSize: $pageSize) {
        id
        name
        description
        path
        meta
        teamId
        experimentId
        runId
        userId
        createdAt
        updatedAt
      }
    }
  `,

  listAgents: `
    query ListAgents($teamId: ID!, $page: Int, $pageSize: Int) {
      agents(teamId: $teamId, page: $page, pageSize: $pageSize) {
        id
        teamId
        userId
        name
        type
        description
        meta
        createdAt
        updatedAt
      }
    }
  `,

  getAgent: `
    query GetAgent($id: ID!) {
      agent(id: $id) {
        id
        teamId
        userId
        name
        type
        description
        meta
        createdAt
        updatedAt
      }
    }
  `,

  listAllSessions: `
    query ListAllSessions($teamId: ID!, $page: Int, $pageSize: Int) {
      team(id: $teamId) {
        id
        agents(page: 0, pageSize: 1000) {
          id
          sessions(page: $page, pageSize: $pageSize) {
            id
            agentId
            teamId
            userId
            meta
            createdAt
            updatedAt
          }
        }
      }
    }
  `,

  listAllAgentRuns: `
    query ListAllAgentRuns($teamId: ID!, $page: Int, $pageSize: Int) {
      team(id: $teamId) {
        id
        agents(page: 0, pageSize: 1000) {
          id
          sessions(page: 0, pageSize: 1000) {
            id
            runs(page: $page, pageSize: $pageSize) {
              id
              teamId
              userId
              sessionId
              status
              duration
              createdAt
            }
          }
        }
      }
    }
  `,

  getSession: `
    query GetSession($sessionId: ID!) {
      session(sessionId: $sessionId) {
        id
        agentId
        teamId
        userId
        meta
        createdAt
        updatedAt
      }
    }
  `,

};

// GraphQL mutation templates
export const mutations = {
  deleteExperiment: `
    mutation DeleteExperiment($experimentId: ID!) {
      deleteExperiment(experimentId: $experimentId)
    }
  `,

  deleteExperiments: `
    mutation DeleteExperiments($experimentIds: [ID!]!) {
      deleteExperiments(experimentIds: $experimentIds)
    }
  `,

  deleteDataset: `
    mutation DeleteDataset($datasetId: ID!) {
      deleteDataset(datasetId: $datasetId)
    }
  `,

  deleteDatasets: `
    mutation DeleteDatasets($datasetIds: [ID!]!) {
      deleteDatasets(datasetIds: $datasetIds)
    }
  `,
};
