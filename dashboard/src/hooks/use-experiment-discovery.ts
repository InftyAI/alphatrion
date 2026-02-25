import { useState, useEffect, useRef } from "react";
import { fetchExperiments, fetchTrials, fetchProjects } from "../services/graphql";

interface ExperimentDiscoveryResult {
    trialId: string | null;
    experimentId: string | null;
    isSearching: boolean;
    error: string | null;
    /** True if experiment was found but still waiting for trials */
    experimentFound: boolean;
}

/**
 * Hook to poll for an experiment by name until it appears in the backend.
 * Searches across ALL projects since experiments may be created in a new project.
 * Once found, it also fetches the first trial ID for that experiment.
 *
 * @param experimentName - The experiment name to search for (null to disable polling)
 * @param _projectId - Unused, kept for API compatibility (we search all projects)
 * @param pollInterval - Polling interval in ms (default: 5000)
 * @param timeout - Timeout in ms (default: 120000 = 2 minutes)
 */
export function useExperimentDiscovery(
    experimentName: string | null,
    _projectId: string | null,
    pollInterval = 5000,
    timeout = 120000
): ExperimentDiscoveryResult {
    const [trialId, setTrialId] = useState<string | null>(null);
    const [experimentId, setExperimentId] = useState<string | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [experimentFound, setExperimentFound] = useState(false);

    const startTimeRef = useRef<number>(0);
    const abortRef = useRef(false);

    useEffect(() => {
        if (!experimentName) {
            setIsSearching(false);
            setTrialId(null);
            setExperimentId(null);
            setError(null);
            setExperimentFound(false);
            return;
        }

        abortRef.current = false;
        startTimeRef.current = Date.now();
        setIsSearching(true);
        setTrialId(null);
        setExperimentId(null);
        setError(null);
        setExperimentFound(false);

        const poll = async () => {
            while (!abortRef.current) {
                // Check for timeout
                if (Date.now() - startTimeRef.current > timeout) {
                    setError("Timed out waiting for experiment to appear");
                    setIsSearching(false);
                    return;
                }

                try {
                    // Fetch all projects first
                    const projects = await fetchProjects();
                    console.log("[ExperimentDiscovery] Looking for:", experimentName);
                    console.log("[ExperimentDiscovery] Searching across", projects.length, "projects");

                    // Normalize the search name (lowercase, spaces to hyphens) to match backend behavior
                    const normalizedSearchName = experimentName.toLowerCase().replace(/\s+/g, '-');
                    console.log("[ExperimentDiscovery] Normalized search name:", normalizedSearchName);

                    // Search for experiment across all projects
                    for (const project of projects) {
                        const experiments = await fetchExperiments({ projectId: project.id });
                        console.log(`[ExperimentDiscovery] Project "${project.name}" has experiments:`, experiments.map(e => e.name));

                        // Look for experiment matching the normalized name
                        const found = experiments.find((exp) =>
                            exp.name === experimentName ||
                            exp.name === normalizedSearchName ||
                            exp.name.toLowerCase() === normalizedSearchName
                        );

                        if (found) {
                            console.log("[ExperimentDiscovery] Found experiment:", found.name, "in project:", project.name);
                            setExperimentId(found.id);
                            setExperimentFound(true);

                            // Now fetch trials for this experiment
                            const trials = await fetchTrials({ experimentId: found.id });
                            console.log("[ExperimentDiscovery] Found trials:", trials.length, trials.map(t => t.id));

                            if (trials.length > 0) {
                                // Return the first trial (most recently created based on usual ordering)
                                console.log("[ExperimentDiscovery] Success! Trial ID:", trials[0].id);
                                setTrialId(trials[0].id);
                                setIsSearching(false);
                                return;
                            } else {
                                console.log("[ExperimentDiscovery] Experiment found but no trials yet, continuing to poll...");
                            }
                        }
                    }
                } catch (err) {
                    console.error("[ExperimentDiscovery] Poll error:", err);
                    // Continue polling despite errors
                }

                // Wait before next poll
                await new Promise((resolve) => setTimeout(resolve, pollInterval));
            }
        };

        poll();

        return () => {
            abortRef.current = true;
        };
    }, [experimentName, pollInterval, timeout]);

    return { trialId, experimentId, isSearching, error, experimentFound };
}
