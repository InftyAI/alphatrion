import type { GraphQLResponse } from "../types";

const GRAPHQL_ENDPOINT =
    import.meta.env.VITE_GRAPHQL_ENDPOINT || "http://127.0.0.1:8000/graphql";

/**
 * Generic GraphQL client using fetch
 */
export async function graphqlRequest<T>(
    query: string,
    variables?: Record<string, unknown>
): Promise<T> {
    const response = await fetch(GRAPHQL_ENDPOINT, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            query,
            variables,
        }),
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: GraphQLResponse<T> = await response.json();

    if (result.errors && result.errors.length > 0) {
        throw new Error(result.errors.map((e) => e.message).join(", "));
    }

    return result.data;
}

// ============================================
// Typed API functions
// ============================================
import type {
    Project,
    Experiment,
    Trial,
    Run,
    Metric,
    ExperimentsQueryParams,
    TrialsQueryParams,
    RunsQueryParams,
    TrialMetricsQueryParams,
    PaginationParams,
} from "../types";

import {
    LIST_PROJECTS,
    GET_PROJECT,
    LIST_EXPERIMENTS,
    GET_EXPERIMENT,
    LIST_TRIALS,
    GET_TRIAL,
    LIST_RUNS,
    GET_RUN,
    LIST_TRIAL_METRICS,
} from "../graphql/queries";

// Projects
export const fetchProjects = async (
    params?: PaginationParams
): Promise<Project[]> => {
    const data = await graphqlRequest<{ projects: Project[] }>(LIST_PROJECTS, {
        page: params?.page ?? 0,
        pageSize: params?.pageSize ?? 100,
    });
    return data.projects;
};

export const fetchProject = async (id: string): Promise<Project | null> => {
    const data = await graphqlRequest<{ project: Project | null }>(GET_PROJECT, {
        id,
    });
    return data.project;
};

// Experiments
export const fetchExperiments = async (
    params: ExperimentsQueryParams
): Promise<Experiment[]> => {
    const data = await graphqlRequest<{ experiments: Experiment[] }>(
        LIST_EXPERIMENTS,
        {
            projectId: params.projectId,
            page: params.page ?? 0,
            pageSize: params.pageSize ?? 100,
        }
    );
    return data.experiments;
};

export const fetchExperiment = async (
    id: string
): Promise<Experiment | null> => {
    const data = await graphqlRequest<{ experiment: Experiment | null }>(
        GET_EXPERIMENT,
        { id }
    );
    return data.experiment;
};

// Trials
export const fetchTrials = async (
    params: TrialsQueryParams
): Promise<Trial[]> => {
    const data = await graphqlRequest<{ trials: Trial[] }>(LIST_TRIALS, {
        experimentId: params.experimentId,
        page: params.page ?? 0,
        pageSize: params.pageSize ?? 100,
    });
    return data.trials;
};

export const fetchTrial = async (id: string): Promise<Trial | null> => {
    const data = await graphqlRequest<{ trial: Trial | null }>(GET_TRIAL, { id });
    return data.trial;
};

// Runs
export const fetchRuns = async (params: RunsQueryParams): Promise<Run[]> => {
    const data = await graphqlRequest<{ runs: Run[] }>(LIST_RUNS, {
        trialId: params.trialId,
        page: params.page ?? 0,
        pageSize: params.pageSize ?? 100,
    });
    return data.runs;
};

export const fetchRun = async (id: string): Promise<Run | null> => {
    const data = await graphqlRequest<{ run: Run | null }>(GET_RUN, { id });
    return data.run;
};

// Metrics
export const fetchTrialMetrics = async (
    params: TrialMetricsQueryParams
): Promise<Metric[]> => {
    const data = await graphqlRequest<{ trialMetrics: Metric[] }>(
        LIST_TRIAL_METRICS,
        {
            trialId: params.trialId,
            page: params.page ?? 0,
            pageSize: params.pageSize ?? 1000, // metrics usually need more
        }
    );
    return data.trialMetrics;
};