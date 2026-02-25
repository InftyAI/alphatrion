import { useQuery } from "@tanstack/react-query";
import { fetchTrials, fetchTrial } from "../services/graphql";

export function useTrials(experimentId: string | null) {
    return useQuery({
        queryKey: ["trials", experimentId],
        queryFn: () => fetchTrials({ experimentId: experimentId! }),
        enabled: !!experimentId, // Only fetch when experimentId is available
    });
}

export function useTrial(id: string | null) {
    return useQuery({
        queryKey: ["trial", id],
        queryFn: () => fetchTrial(id!),
        enabled: !!id,
    });
}
