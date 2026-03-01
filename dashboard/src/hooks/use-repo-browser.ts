import { useState, useEffect, useCallback } from "react";
import type { RepoFileTree, RepoFileContent } from "../types";
import { fetchRepoFileTree, fetchRepoFileContent } from "../lib/graphql-client";

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
 * Hook for fetching the repository file tree for an experiment.
 */
export function useRepoFileTree(experimentId: string | null): UseRepoFileTreeResult {
    const [tree, setTree] = useState<RepoFileTree | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);

    useEffect(() => {
        if (!experimentId) {
            setTree(null);
            return;
        }

        const loadTree = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const result = await fetchRepoFileTree(experimentId);
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
    }, [experimentId, refreshKey]);

    const refresh = useCallback(() => {
        setRefreshKey((k) => k + 1);
    }, []);

    return { tree, isLoading, error, refresh };
}

/**
 * Hook for fetching file content from an experiment's repository.
 */
export function useRepoFileContent(
    experimentId: string | null
): UseRepoFileContentResult {
    const [content, setContent] = useState<RepoFileContent | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const loadFile = useCallback(
        async (filePath: string) => {
            if (!experimentId) {
                return;
            }

            setIsLoading(true);
            setError(null);
            try {
                const result = await fetchRepoFileContent(experimentId, filePath);
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
        [experimentId]
    );

    const clearContent = useCallback(() => {
        setContent(null);
        setError(null);
    }, []);

    return { content, isLoading, error, loadFile, clearContent };
}
