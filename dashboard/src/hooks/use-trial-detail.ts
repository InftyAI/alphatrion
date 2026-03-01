import { useQuery } from "@tanstack/react-query";
import { fetchMetricKeys, graphqlQuery, queries } from "../lib/graphql-client";
import type { Run, Experiment } from "../types";

export function useExperimentDetailIDE(experimentId: string | null, options?: { refetchInterval?: number | false }) {
    const experimentQuery = useQuery({
        queryKey: ["experiment", experimentId],
        queryFn: async () => {
            const data = await graphqlQuery<{ experiment: Experiment }>(queries.getExperiment, { id: experimentId });
            return data.experiment;
        },
        enabled: !!experimentId,
        refetchInterval: options?.refetchInterval,
    });

    const runsQuery = useQuery({
        queryKey: ["runs", experimentId],
        queryFn: async () => {
            const data = await graphqlQuery<{ runs: Run[] }>(
                `query ListRuns($experimentId: ID!) {
                    runs(experimentId: $experimentId) {
                        id
                        teamId
                        userId
                        experimentId
                        meta
                        status
                        createdAt
                    }
                }`,
                { experimentId }
            );
            return data.runs;
        },
        enabled: !!experimentId,
        refetchInterval: options?.refetchInterval,
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
        refetchOnMount: "always",
        refetchInterval: options?.refetchInterval,
    });

    return {
        metricKeys: query.data ?? [],
        metricKeysLoading: query.isLoading,
        metricKeysError: query.error,
    };
}
