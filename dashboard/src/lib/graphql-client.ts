import axios from 'axios';

/**
 * GraphQL client for AlphaTrion backend
 *
 * The backend provides a read-only GraphQL API at /graphql
 * with queries for teams, projects, experiments, runs, and metrics.
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
    query ListTeams {
      teams {
        id
        name
        description
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
      }
    }
  `,

  listProjects: `
    query ListProjects($teamId: ID!, $page: Int, $pageSize: Int) {
      projects(teamId: $teamId, page: $page, pageSize: $pageSize) {
        id
        teamId
        creatorId
        name
        description
        meta
        createdAt
        updatedAt
      }
    }
  `,

  getProject: `
    query GetProject($id: ID!) {
      project(id: $id) {
        id
        teamId
        creatorId
        name
        description
        meta
        createdAt
        updatedAt
      }
    }
  `,

  listExperiments: `
    query ListExperiments($projectId: ID!, $page: Int, $pageSize: Int) {
      experiments(projectId: $projectId, page: $page, pageSize: $pageSize) {
        id
        teamId
        userId
        projectId
        name
        description
        kind
        meta
        params
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
        projectId
        name
        description
        kind
        meta
        params
        duration
        status
        createdAt
        updatedAt
      }
    }
  `,

  listRuns: `
    query ListRuns($experimentId: ID!, $page: Int, $pageSize: Int) {
      runs(experimentId: $experimentId, page: $page, pageSize: $pageSize) {
        id
        teamId
        userId
        projectId
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
        projectId
        experimentId
        meta
        status
        createdAt
      }
    }
  `,

  listMetrics: `
    query ListMetrics($experimentId: ID!) {
      experimentMetrics(experimentId: $experimentId) {
        id
        key
        value
        teamId
        projectId
        experimentId
        runId
        createdAt
      }
    }
  `,

  getStatistics: `
    query GetStatistics($teamId: ID!) {
      statistics(teamId: $teamId) {
        totalProjects
        totalExperiments
        totalRuns
      }
    }
  `,
};
