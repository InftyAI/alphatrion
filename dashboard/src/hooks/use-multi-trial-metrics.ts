import { useQueries } from "@tanstack/react-query";
import { fetchTrialMetrics } from "../services/graphql";

export function useMultiTrialMetrics(trialIds: string[]) {
    const queries = useQueries({
        queries: trialIds.map((trialId) => ({
            queryKey: ["trialMetrics", trialId],
            queryFn: () => fetchTrialMetrics({ trialId }),
            enabled: !!trialId,
        })),
    });

    const isLoading = queries.some((q) => q.isLoading);
    const error = queries.find((q) => q.error)?.error;

    // Combine all metrics with trial information
    const metricsWithTrial = queries.flatMap((q, idx) => {
        if (!q.data) return [];
        return q.data.map((metric: any) => ({
            ...metric,
            trialId: trialIds[idx],
        }));
    });

    return {
        metrics: metricsWithTrial,
        isLoading,
        error,
    };
}
