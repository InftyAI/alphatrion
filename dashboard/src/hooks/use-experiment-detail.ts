import { useQuery } from "@tanstack/react-query";
import { fetchExperiment, fetchTrials } from "../services/graphql";

export function useExperimentDetail(experimentId: string | null) {
    const experimentQuery = useQuery({
        queryKey: ["experiment", experimentId],
        queryFn: () => fetchExperiment(experimentId!),
        enabled: !!experimentId,
    });

    const trialsQuery = useQuery({
        queryKey: ["trials", experimentId],
        queryFn: () => fetchTrials({ experimentId: experimentId! }),
        enabled: !!experimentId,
    });

    return {
        experiment: experimentQuery.data,
        trials: trialsQuery.data ?? [],
        isLoading: experimentQuery.isLoading || trialsQuery.isLoading,
        error: experimentQuery.error || trialsQuery.error,
    };
}