/**
 * AI Studio Experiment Types
 * Migrated from trial types in the forked project
 */

export type GraphQLStatus = "UNKNOWN" | "PENDING" | "RUNNING" | "CANCELLED" | "COMPLETED" | "FAILED";

export interface Experiment {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  name: string;
  description: string | null;
  kind: number;
  meta: Record<string, unknown> | null;
  params: Record<string, unknown> | null;
  duration: number;
  status: GraphQLStatus;
  createdAt: string;
  updatedAt: string;
}

export interface Run {
  id: string;
  teamId: string;
  userId: string;
  projectId: string;
  experimentId: string;
  meta: Record<string, unknown> | null;
  status: GraphQLStatus;
  createdAt: string;
}

export interface Metric {
  id: string;
  key: string;
  value: number;
  teamId: string;
  projectId: string;
  experimentId: string;
  runId: string;
  createdAt: string;
}

export interface ExperimentWithRuns extends Experiment {
  runs?: Run[];
  metrics?: Metric[];
  metricKeys?: string[];
}
