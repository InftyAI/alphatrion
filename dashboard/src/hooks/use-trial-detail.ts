import { useQuery } from "@tanstack/react-query";
import { fetchTrial, fetchRuns, fetchTrialMetrics, fetchMetricKeys } from "../services/graphql";

export function useTrialDetail(trialId: string | null, options?: { refetchInterval?: number | false }) {
    const trialQuery = useQuery({
        queryKey: ["trial", trialId],
        queryFn: () => fetchTrial(trialId!),
        enabled: !!trialId,
        refetchInterval: options?.refetchInterval,
    });

    const runsQuery = useQuery({
        queryKey: ["runs", trialId],
        queryFn: () => fetchRuns({ trialId: trialId! }),
        enabled: !!trialId,
        refetchInterval: options?.refetchInterval,
    });

    return {
        trial: trialQuery.data,
        runs: runsQuery.data ?? [],
        runsLoading: runsQuery.isLoading,
        isLoading: trialQuery.isLoading,
        error: trialQuery.error || runsQuery.error,
    };
}

export function useTrialMetrics(trialId: string | null, enabled: boolean = true) {
    const metricsQuery = useQuery({
        queryKey: ["trialMetrics", trialId],
        queryFn: () => fetchTrialMetrics({ trialId: trialId! }),
        enabled: !!trialId && enabled,
    });

    return {
        metrics: metricsQuery.data ?? [],
        metricsLoading: metricsQuery.isLoading,
        metricsError: metricsQuery.error,
    };
}

export function useMetricKeys(trialId: string | null, options?: { refetchInterval?: number | false }) {
    const query = useQuery({
        queryKey: ["metricKeys", trialId],
        queryFn: () => fetchMetricKeys(trialId!),
        enabled: !!trialId,
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
