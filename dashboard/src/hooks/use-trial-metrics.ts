import { useQuery } from "@tanstack/react-query";
import { fetchTrialMetrics } from "../services/graphql";

export function useTrialMetrics(trialId: string | null) {
    return useQuery({
        queryKey: ["trialMetrics", trialId],
        queryFn: () => fetchTrialMetrics({ trialId: trialId! }),
        enabled: !!trialId,
    });
}