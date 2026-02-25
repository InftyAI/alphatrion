import { useQuery } from "@tanstack/react-query";
import { fetchTrialMetrics } from "../services/graphql";

export function useTrialMetricsHook(trialId: string | null) {
    return useQuery({
        queryKey: ["trialMetrics", trialId],
        queryFn: () => fetchTrialMetrics({ trialId: trialId! }),
        enabled: !!trialId,
        retry: 1,
    });
}
