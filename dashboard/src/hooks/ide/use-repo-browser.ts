import { useState, useEffect, useCallback } from "react";
import type { RepoFileTree, RepoFileContent } from "../types";
import { fetchRepoFileTree, fetchRepoFileContent } from "../services/graphql";

interface UseRepoFileTreeResult {
    tree: RepoFileTree | null;
    isLoading: boolean;
    error: Error | null;
    refresh: () => void;
}

interface UseRepoFileContentResult {
    content: RepoFileContent | null;
    isLoading: boolean;
    error: Error | null;
    loadFile: (filePath: string) => Promise<void>;
    clearContent: () => void;
}

/**
 * Hook for fetching the repository file tree for a trial.
 */
export function useRepoFileTree(trialId: string | null): UseRepoFileTreeResult {
    const [tree, setTree] = useState<RepoFileTree | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);

    useEffect(() => {
        if (!trialId) {
            setTree(null);
            return;
        }

        const loadTree = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const result = await fetchRepoFileTree(trialId);
                setTree(result);
            } catch (err) {
                setError(
                    err instanceof Error ? err : new Error("Failed to load file tree")
                );
                setTree(null);
            } finally {
                setIsLoading(false);
            }
        };

        loadTree();
    }, [trialId, refreshKey]);

    const refresh = useCallback(() => {
        setRefreshKey((k) => k + 1);
    }, []);

    return { tree, isLoading, error, refresh };
}

/**
 * Hook for fetching file content from a trial's repository.
 */
export function useRepoFileContent(
    trialId: string | null
): UseRepoFileContentResult {
    const [content, setContent] = useState<RepoFileContent | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const loadFile = useCallback(
        async (filePath: string) => {
            if (!trialId) {
                return;
            }

            setIsLoading(true);
            setError(null);
            try {
                const result = await fetchRepoFileContent(trialId, filePath);
                setContent(result);
            } catch (err) {
                setError(
                    err instanceof Error ? err : new Error("Failed to load file content")
                );
                setContent(null);
            } finally {
                setIsLoading(false);
            }
        },
        [trialId]
    );

    const clearContent = useCallback(() => {
        setContent(null);
        setError(null);
    }, []);

    return { content, isLoading, error, loadFile, clearContent };
}
