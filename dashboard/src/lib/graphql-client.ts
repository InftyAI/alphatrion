import axios from 'axios';

/**
 * GraphQL client for AlphaTrion backend
 *
 * The backend provides a GraphQL API at /graphql
 * with queries and mutations for teams, experiments, runs, and metrics.
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
};
