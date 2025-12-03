import { useQuery } from "@tanstack/react-query";
import { fetchRuns, fetchRun } from "../services/graphql";

export function useRuns(trialId: string | null) {
    return useQuery({
        queryKey: ["runs", trialId],
        queryFn: () => fetchRuns({ trialId: trialId! }),
        enabled: !!trialId,
    });
}

export function useRun(id: string | null) {
    return useQuery({
        queryKey: ["run", id],
        queryFn: () => fetchRun(id!),
        enabled: !!id,
    });
}