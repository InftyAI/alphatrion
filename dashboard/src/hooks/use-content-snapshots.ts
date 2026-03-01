import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ContentSnapshot, ContentSnapshotSummary } from "../types";
import {
    fetchContentSnapshotsSummary,
    fetchContentLineage,
    fetchContentSnapshot,
} from "../lib/graphql-client";

// Use this for the chart - lightweight version without content_text
export function useContentSnapshotsSummary(experimentId: string | null, options?: { refetchInterval?: number | false }) {
    const { data, isLoading, error } = useQuery({
        queryKey: ["contentSnapshotsSummary", experimentId],
        queryFn: () => fetchContentSnapshotsSummary({ experimentId: experimentId! }),
        enabled: !!experimentId,
        refetchInterval: options?.refetchInterval,
    });

    return { snapshots: data ?? [], isLoading, error };
}

// Hook to fetch a single content snapshot by ID — imperative with cache
export function useContentSnapshotById() {
    const queryClient = useQueryClient();
    const [snapshot, setSnapshot] = useState<ContentSnapshot | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const loadSnapshot = useCallback(async (id: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await queryClient.fetchQuery({
                queryKey: ["contentSnapshot", id],
                queryFn: () => fetchContentSnapshot(id),
            });
            setSnapshot(data);
        } catch (err) {
            setError(err as Error);
        } finally {
            setIsLoading(false);
        }
    }, [queryClient]);

    const clearSnapshot = useCallback(() => {
        setSnapshot(null);
    }, []);

    return { snapshot, isLoading, error, loadSnapshot, clearSnapshot };
}

export function useContentLineage() {
    const queryClient = useQueryClient();
    const [lineage, setLineage] = useState<ContentSnapshot[] | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const loadLineage = useCallback(async (experimentId: string, contentUid: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await queryClient.fetchQuery({
                queryKey: ["contentLineage", experimentId, contentUid],
                queryFn: () => fetchContentLineage({ experimentId, contentUid }),
            });
            setLineage(data);
        } catch (err) {
            setError(err as Error);
        } finally {
            setIsLoading(false);
        }
    }, [queryClient]);

    const clearLineage = useCallback(() => {
        setLineage(null);
    }, []);

    return { lineage, isLoading, error, loadLineage, clearLineage };
}
