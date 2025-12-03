import { useQuery } from "@tanstack/react-query";
import { fetchExperiments, fetchExperiment } from "../services/graphql";

export function useExperiments(projectId: string | null) {
    return useQuery({
        queryKey: ["experiments", projectId],
        queryFn: () => fetchExperiments({ projectId: projectId! }),
        enabled: !!projectId, // Only fetch when projectId is available
    });
}

export function useExperiment(id: string | null) {
    return useQuery({
        queryKey: ["experiment", id],
        queryFn: () => fetchExperiment(id!),
        enabled: !!id,
    });
}