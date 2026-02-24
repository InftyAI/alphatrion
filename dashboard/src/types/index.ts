// Core types matching GraphQL schema
// Note: This uses correct terminology (Experiment, not Trial)

export enum Status {
  UNKNOWN = "UNKNOWN",
  PENDING = "PENDING",
  RUNNING = "RUNNING",
  CANCELLED = "CANCELLED",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export enum ExperimentType {
  UNKNOWN = 0,
  CRAFT_EXPERIMENT = 1,
}

export interface Team {
  id: string;
  name: string | null;
  description: string | null;
  meta: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
  totalProjects: number;
  totalExperiments: number;
  totalRuns: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  teamId: string;
  meta: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  teamId: string;
  creatorId: string;
  name: string | null;
  description: string | null;
  meta: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface Experiment {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  name: string;
  description: string | null;
  kind: ExperimentType;
  meta: Record<string, unknown> | null;
  params: Record<string, unknown> | null;
  duration: number;
  status: Status;
  createdAt: string;
  updatedAt: string;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  metrics?: Metric[];
}

export interface Run {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  experimentId: string;
  meta: Record<string, unknown> | null;
  status: Status;
  createdAt: string;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  metrics?: Metric[];
  spans?: Span[];
}

export interface Metric {
  id: string;
  key: string | null;
  value: number | null;
  teamId: string;
  projectId: string;
  experimentId: string;
  runId: string;
  createdAt: string;
}

// Grouped metrics for chart rendering
export interface GroupedMetrics {
  [key: string]: Metric[];
}

// Artifact types for ORAS registry
export interface ArtifactRepository {
  name: string;
  tags: string[];
}

export interface ArtifactManifest {
  schemaVersion: number;
  mediaType: string;
  config: {
    mediaType: string;
    digest: string;
    size: number;
  };
  layers: Array<{
    mediaType: string;
    digest: string;
    size: number;
    annotations?: Record<string, string>;
  }>;
  annotations?: Record<string, string>;
}

export interface ArtifactBlob {
  digest: string;
  content: Blob | string;
  mediaType: string;
}

// Comparison context types
export interface ComparisonState {
  selectedExperimentIds: string[];
  addExperiment: (id: string) => void;
  removeExperiment: (id: string) => void;
  clearSelection: () => void;
}

// Pareto frontier types
export interface MetricConfig {
  key: string;
  direction: 'maximize' | 'minimize';
}

export interface RunMetrics {
  runId: string;
  metrics: Record<string, number>;
  isPareto?: boolean;
}

// Trace types
export interface TraceEvent {
  timestamp: string;
  name: string;
  attributes: Record<string, string>;
}

export interface TraceLink {
  traceId: string;
  spanId: string;
  attributes: Record<string, string>;
}

export interface Span {
  timestamp: string;
  traceId: string;
  spanId: string;
  parentSpanId: string;
  spanName: string;
  spanKind: string;
  semanticKind: string;
  serviceName: string;
  duration: number; // nanoseconds (received as float from GraphQL)
  statusCode: string;
  statusMessage: string;
  teamId: string;
  projectId: string;
  runId: string;
  experimentId: string;
  spanAttributes: Record<string, string>;
  resourceAttributes: Record<string, string>;
  events: TraceEvent[];
  links: TraceLink[];
}
