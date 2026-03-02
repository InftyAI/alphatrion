import { useQuery } from "@tanstack/react-query";
import { fetchMetricKeys, graphqlQuery, queries } from "../lib/graphql-client";
import type { Run, Experiment } from "../types";

export function useExperimentDetailIDE(experimentId: string | null, options?: { refetchInterval?: number | false }) {
    const experimentQuery = useQuery({
        queryKey: ["experiment", experimentId, "with-metrics"],
        queryFn: async () => {
            const data = await graphqlQuery<{ experiment: Experiment }>(queries.getExperiment, { id: experimentId });
            return data.experiment;
        },
        enabled: !!experimentId,
        refetchInterval: options?.refetchInterval,
        staleTime: 60000, // Cache for 1 minute - reuse if navigating from experiment detail page
    });

    const runsQuery = useQuery({
        queryKey: ["runs", experimentId, 0, 10000], // Match standard useRuns cache key format
        queryFn: async () => {
            const data = await graphqlQuery<{ runs: Run[] }>(
                queries.listRuns,
                { experimentId, page: 0, pageSize: 10000 }
            );
            return data.runs;
        },
        enabled: !!experimentId,
        refetchInterval: options?.refetchInterval,
        staleTime: 60000, // Cache for 1 minute
    });

    return {
        experiment: experimentQuery.data,
        runs: runsQuery.data ?? [],
        runsLoading: runsQuery.isLoading,
        isLoading: experimentQuery.isLoading,
        error: experimentQuery.error || runsQuery.error,
    };
}

export function useMetricKeys(experimentId: string | null, options?: { refetchInterval?: number | false }) {
    const query = useQuery({
        queryKey: ["metricKeys", experimentId],
        queryFn: () => fetchMetricKeys(experimentId!),
        enabled: !!experimentId,
        retry: 2,
        retryDelay: 1000,
        staleTime: 60000, // Cache for 1 minute
        refetchInterval: options?.refetchInterval,
    });

    return {
        metricKeys: query.data ?? [],
        metricKeysLoading: query.isLoading,
        metricKeysError: query.error,
    };
}
