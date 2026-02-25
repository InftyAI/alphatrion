import { useState, useCallback } from "react";
import type { AnalyzeResponse, AnalysisFinding } from "../types";
import { analyzeTrialCode } from "../services/graphql";

interface UseAnalyzeResult {
    findings: AnalysisFinding[];
    isAnalyzing: boolean;
    error: Error | null;
    analyze: (trialName: string) => Promise<void>;
    clearAnalysis: () => void;
}

/**
 * Hook for analyzing trial code using Claude CLI.
 */
export function useAnalyze(): UseAnalyzeResult {
    const [findings, setFindings] = useState<AnalysisFinding[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const analyze = useCallback(async (trialName: string) => {
        setIsAnalyzing(true);
        setError(null);
        setFindings([]);

        try {
            const result = await analyzeTrialCode(trialName);
            if (result.error) {
                setError(new Error(result.error));
            }
            setFindings(result.findings || []);
        } catch (err) {
            setError(
                err instanceof Error ? err : new Error("Failed to analyze code")
            );
        } finally {
            setIsAnalyzing(false);
        }
    }, []);

    const clearAnalysis = useCallback(() => {
        setFindings([]);
        setError(null);
    }, []);

    return { findings, isAnalyzing, error, analyze, clearAnalysis };
}
