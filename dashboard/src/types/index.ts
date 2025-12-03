// GraphQL Status Enum
export type GraphQLStatus =
    | "UNKNOWN"
    | "PENDING"
    | "RUNNING"
    | "CANCELLED"
    | "COMPLETED"
    | "FAILED";

// Base Types matching Alphatrion GraphQL Schema
export interface Project {
    id: string;
    name: string | null;
    description: string | null;
    createdAt: string;
    updatedAt: string;
}

export interface Experiment {
    id: string;
    projectId: string | null;
    name: string | null;
    description: string | null;
    meta: Record<string, unknown> | null;
    createdAt: string;
    updatedAt: string;
}

export interface Trial {
    id: string;
    experimentId: string;
    projectId: string;
    name: string;
    description: string | null;
    meta: Record<string, unknown> | null;
    params: Record<string, unknown> | null;
    duration: number;
    status: GraphQLStatus;
    createdAt: string;
    updatedAt: string;
}

export interface Run {
    id: string;
    trialId: string;
    projectId: string;
    experimentId: string;
    meta: Record<string, unknown> | null;
    status: GraphQLStatus;
    createdAt: string;
}

export interface Metric {
    id: string;
    key: string | null;
    value: number | null;
    projectId: string;
    experimentId: string;
    trialId: string;
    runId: string;
    step: number;
    createdAt: string;
}

// GraphQL Response Types
export interface GraphQLResponse<T> {
    data: T;
    errors?: Array<{ message: string }>;
}

// Paginated List Params
export interface PaginationParams {
    page?: number;
    pageSize?: number;
}

// Query Params for each entity
export interface ExperimentsQueryParams extends PaginationParams {
    projectId: string;
}

export interface TrialsQueryParams extends PaginationParams {
    experimentId: string;
}

export interface RunsQueryParams extends PaginationParams {
    trialId: string;
}

export interface TrialMetricsQueryParams extends PaginationParams {
    trialId: string;
}