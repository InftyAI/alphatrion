import { useQuery } from "@tanstack/react-query";
import { fetchTrial, fetchRuns, fetchTrialMetrics } from "../services/graphql";

export function useTrialDetail(trialId: string | null) {
    const trialQuery = useQuery({
        queryKey: ["trial", trialId],
        queryFn: () => fetchTrial(trialId!),
        enabled: !!trialId,
    });

    const runsQuery = useQuery({
        queryKey: ["runs", trialId],
        queryFn: () => fetchRuns({ trialId: trialId! }),
        enabled: !!trialId,
    });

    const metricsQuery = useQuery({
        queryKey: ["trialMetrics", trialId],
        queryFn: () => fetchTrialMetrics({ trialId: trialId! }),
        enabled: !!trialId,
    });

    return {
        trial: trialQuery.data,
        runs: runsQuery.data ?? [],
        metrics: metricsQuery.data ?? [],
        isLoading: trialQuery.isLoading || runsQuery.isLoading || metricsQuery.isLoading,
        error: trialQuery.error || runsQuery.error || metricsQuery.error,
    };
}