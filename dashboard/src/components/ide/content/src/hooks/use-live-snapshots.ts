import { useState, useEffect, useRef, useCallback } from "react";
import type { ContentSnapshotSummary, Trial } from "../types";
import { fetchContentSnapshotsSummary, fetchTrial } from "../services/graphql";

interface LiveSnapshotsResult {
    snapshots: ContentSnapshotSummary[];
    trial: Trial | null;
    isLoading: boolean;
    error: string | null;
    isActive: boolean;
}

/**
 * Hook for polling content snapshots during an active experiment.
 * Automatically stops polling when the trial status is COMPLETED, FAILED, or CANCELLED.
 *
 * @param trialId - The trial ID to poll snapshots for (null to disable)
 * @param pollInterval - Polling interval in ms (default: 5000)
 */
export function useLiveSnapshots(
    trialId: string | null,
    pollInterval = 5000
): LiveSnapshotsResult {
    const [snapshots, setSnapshots] = useState<ContentSnapshotSummary[]>([]);
    const [trial, setTrial] = useState<Trial | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isActive, setIsActive] = useState(false);

    const abortRef = useRef(false);

    // Terminal statuses that should stop polling
    const isTerminalStatus = useCallback((status: string) => {
        return ["COMPLETED", "FAILED", "CANCELLED"].includes(status);
    }, []);

    useEffect(() => {
        if (!trialId) {
            setSnapshots([]);
            setTrial(null);
            setIsLoading(false);
            setError(null);
            setIsActive(false);
            return;
        }

        abortRef.current = false;
        setIsLoading(true);
        setIsActive(true);
        setError(null);

        const poll = async () => {
            // Initial fetch
            try {
                const [snapshotsData, trialData] = await Promise.all([
                    fetchContentSnapshotsSummary({ trialId }),
                    fetchTrial(trialId),
                ]);

                if (abortRef.current) return;

                setSnapshots(snapshotsData);
                setTrial(trialData);
                setIsLoading(false);

                // Check if trial is already in terminal state
                if (trialData && isTerminalStatus(trialData.status)) {
                    setIsActive(false);
                    return;
                }
            } catch (err) {
                if (abortRef.current) return;
                setError(err instanceof Error ? err.message : "Failed to fetch data");
                setIsLoading(false);
                // Continue polling despite initial error
            }

            // Start polling loop
            while (!abortRef.current) {
                await new Promise((resolve) => setTimeout(resolve, pollInterval));

                if (abortRef.current) return;

                try {
                    const [snapshotsData, trialData] = await Promise.all([
                        fetchContentSnapshotsSummary({ trialId }),
                        fetchTrial(trialId),
                    ]);

                    if (abortRef.current) return;

                    setSnapshots(snapshotsData);
                    setTrial(trialData);
                    setError(null);

                    // Stop polling if trial reached terminal state
                    if (trialData && isTerminalStatus(trialData.status)) {
                        setIsActive(false);
                        return;
                    }
                } catch (err) {
                    if (abortRef.current) return;
                    console.error("[LiveSnapshots] Poll error:", err);
                    // Continue polling despite errors
                }
            }
        };

        poll();

        return () => {
            abortRef.current = true;
        };
    }, [trialId, pollInterval, isTerminalStatus]);

    return { snapshots, trial, isLoading, error, isActive };
}
