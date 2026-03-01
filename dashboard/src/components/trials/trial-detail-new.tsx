import { Filter, GitCompare, HelpCircle, Maximize2, Minimize2, RotateCcw } from "lucide-react";
import { memo, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Highlight, themes } from "prism-react-renderer";
import { useContentSnapshotById, useContentSnapshotsSummary } from "../../hooks/use-content-snapshots";
import { useExperiment } from "../../hooks/use-experiments";
import { useRepoFileContent, useRepoFileTree } from "../../hooks/use-repo-browser";
import { useExperimentDetailIDE, useMetricKeys } from "../../hooks/use-trial-detail";
import MetricsTree from "../charts/metrics-tree";
import { useSelection } from "../../App";
import type { ContentSnapshotSummary } from "../../types";
import { computeAllFileDiffs } from "../../utils/file-diff";
import { extractFitnessKeys, getFitnessValue } from "../../utils/fitness";
import { ChatInline } from "../chat";
import ContentComparisonPanel from "../content/content-comparison-panel";
import ContentEvolutionChart, { type ChartViewMode } from "../content/content-evolution-chart";
import LineageHistory from "../content/lineage-history";
import LineageTree from "../content/lineage-tree";
import { FileTree, FileViewer } from "../repo";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { EvaluationResult } from "../ui/json-value";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "../ui/select";

// Ablation flags — set to false to disable a component for performance testing
const DEBUG_ABLATION = {
    chart: true,           // The entire ContentEvolutionChart scatter plot
    lineageLines: true,    // Lineage lines drawn on chart (ancestors/co-parents)
    lineagePanel: true,    // The "Evolution History" panel below the chart
    codeViewer: true,       // Code viewer (middle panel)
    repoTree: true,        // Repository file tree (left panel)
    chatPanel: true,       // Chat panel at bottom of code viewer
    autoSelect: true,      // Auto-select best point on page load
};

// Helper to parse contentText that may have markdown format like "## filename.py\n```python\ncode\n```"
const parseContentText = (contentText: string | undefined): { filename: string | null; code: string } => {
    if (!contentText) return { filename: null, code: "" };
    // Try to match markdown format: ## filename.ext\n```lang\ncode\n```
    const markdownMatch = contentText.match(/^##\s*([^\n]+)\n```[^\n]*\n([\s\S]*?)```\s*$/);
    if (markdownMatch) {
        return {
            filename: markdownMatch[1].trim(),
            code: markdownMatch[2],
        };
    }
    // Try simpler format: ## filename.ext\ncode
    const simpleMatch = contentText.match(/^##\s*([^\n]+)\n([\s\S]*)$/);
    if (simpleMatch) {
        return {
            filename: simpleMatch[1].trim(),
            code: simpleMatch[2],
        };
    }
    // No markdown header, return as-is
    return { filename: null, code: contentText };
};

// Memoized code viewer using prism-react-renderer (lightweight, fewer DOM nodes)
const MemoizedCodeViewer = memo(function MemoizedCodeViewer({ contentText, language }: { contentText?: string; language: string }) {
    const { code } = parseContentText(contentText);
    return (
        <Highlight theme={themes.oneLight} code={code} language={language}>
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
                <pre className={className} style={{ ...style, margin: 0, fontSize: "0.8rem", overflow: "auto" }}>
                    {tokens.map((line, i) => (
                        <div key={i} {...getLineProps({ line })} style={{ display: "table-row" }}>
                            <span style={{
                                display: "table-cell",
                                textAlign: "right",
                                paddingRight: "1em",
                                userSelect: "none",
                                opacity: 0.5,
                                width: "1%",
                                whiteSpace: "nowrap",
                            }}>
                                {i + 1}
                            </span>
                            <span style={{ display: "table-cell" }}>
                                {line.map((token, key) => (
                                    <span key={key} {...getTokenProps({ token })} />
                                ))}
                            </span>
                        </div>
                    ))}
                </pre>
            )}
        </Highlight>
    );
});

export default function TrialDetail() {
    const { id } = useParams<{ id: string }>();
    const [searchParams, setSearchParams] = useSearchParams();
    // Auto-refresh: poll every 60s while trial is ongoing, stop when it completes.
    // On first render trial is undefined so pollInterval is false; once the trial
    // loads and is RUNNING/PENDING, the re-render passes 60_000 to all hooks.
    const [pollInterval, setPollInterval] = useState<number | false>(false);
    const [selectedMetricPaths, setSelectedMetricPaths] = useState<Set<string>>(new Set());
    const { experiment, isLoading, error } = useExperimentDetailIDE(id ?? null, { refetchInterval: pollInterval });
    const { setExperimentId, setExperimentName, setSelectedPointName, chartPanelMode, setChartPanelMode } = useSelection();
    const { snapshot: fullSnapshot, isLoading: snapshotLoading, loadSnapshot: loadFullSnapshot, clearSnapshot: clearFullSnapshot } = useContentSnapshotById();

    const isOngoing = experiment?.status === "RUNNING" || experiment?.status === "PENDING";
    useEffect(() => {
        setPollInterval(isOngoing ? 60_000 : false);
    }, [isOngoing]);

    // Load content snapshots summary (lightweight, no content_text)
    const { snapshots, isLoading: snapshotsLoading } = useContentSnapshotsSummary(id ?? null, { refetchInterval: pollInterval });

    // Prefetch metric keys so they're cached when user switches to metrics view
    useMetricKeys(id ?? null, { refetchInterval: pollInterval });

    // uid→snapshot lookup map (O(1) instead of O(n) find calls)
    const snapshotUidMap = useMemo(() => {
        const map = new Map<string, ContentSnapshotSummary>();
        for (const s of snapshots) {
            map.set(s.contentUid, s);
        }
        return map;
    }, [snapshots]);

    // Build lineage client-side from already-fetched summary data (zero API calls)
    const [lineageUid, setLineageUid] = useState<string | null>(null);
    const lineage = useMemo(() => {
        if (!lineageUid || snapshotUidMap.size === 0) return null;
        const chain: ContentSnapshotSummary[] = [];
        let currentUid: string | null = lineageUid;
        const visited = new Set<string>();
        while (currentUid && !visited.has(currentUid)) {
            visited.add(currentUid);
            const snap = snapshotUidMap.get(currentUid);
            if (snap) {
                chain.push(snap);
                currentUid = snap.parentUid;
            } else {
                break;
            }
        }
        chain.reverse();
        return chain;
    }, [lineageUid, snapshotUidMap]);
    const [highlightedSnapshot, setHighlightedSnapshot] = useState<ContentSnapshotSummary | null>(null);
    // Deferred version for the chart — lets code panel update instantly while chart re-renders in background
    const deferredHighlightedSnapshot = useDeferredValue(highlightedSnapshot);
    const [comparisonMode, setComparisonMode] = useState(false);
    const [comparisonSnapshot1, setComparisonSnapshot1] = useState<ContentSnapshotSummary | null>(null);
    const [comparisonSnapshot2, setComparisonSnapshot2] = useState<ContentSnapshotSummary | null>(null);
    // Full content for comparison (fetched when snapshots are selected)
    const [fullComparisonSnapshot1, setFullComparisonSnapshot1] = useState<import("../../types").ContentSnapshot | null>(null);
    const [fullComparisonSnapshot2, setFullComparisonSnapshot2] = useState<import("../../types").ContentSnapshot | null>(null);
    const [chartMaximized, setChartMaximized] = useState(false);
    const [chartViewMode, setChartViewMode] = useState<ChartViewMode>("evolution");
    const [isChartZoomed, setIsChartZoomed] = useState(false);
    const zoomResetRef = useRef<(() => void) | null>(null);
    const [showLineageModal, setShowLineageModal] = useState(false);
    const [selectedRepoFile, setSelectedRepoFile] = useState<string | null>(null);
    const [showRepoViewer, setShowRepoViewer] = useState(false);
    const [showChatPanel, setShowChatPanel] = useState(false);
    const [belowChartTab, setBelowChartTab] = useState<"history" | "evaluation">("history");
    const [comparisonScrollTarget, setComparisonScrollTarget] = useState<string | null>(null);
    const [showOnlyChangedFiles, setShowOnlyChangedFiles] = useState(false);

    // Resizable lineage panel (vertical) - stored as ratio (0-1)
    const [lineagePanelRatio, setLineagePanelRatio] = useState(0.25); // 25% of container height
    const isResizingVertical = useRef(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Resizable chart panel (horizontal) - stored as ratio (0-1)
    const [chartPanelRatio, setChartPanelRatio] = useState(0.55); // 55% of container width
    const isResizingChart = useRef(false);
    const horizontalContainerRef = useRef<HTMLDivElement>(null);

    // Resizable repo panel (horizontal) - stored as ratio (0-1)
    const [repoPanelRatio, setRepoPanelRatio] = useState(0.15); // 15% of container width
    const isResizingRepo = useRef(false);

    const handleVerticalResizeStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isResizingVertical.current = true;
        document.body.style.cursor = 'row-resize';
        document.body.style.userSelect = 'none';
    }, []);

    const handleChartResizeStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isResizingChart.current = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, []);

    const handleRepoResizeStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isResizingRepo.current = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, []);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isResizingVertical.current && containerRef.current) {
                const containerRect = containerRef.current.getBoundingClientRect();
                const containerHeight = containerRect.height;
                const newHeight = containerRect.bottom - e.clientY;
                const newRatio = newHeight / containerHeight;
                setLineagePanelRatio(Math.max(0.1, Math.min(0.5, newRatio))); // Between 10% and 50%
            }
            if (isResizingChart.current && horizontalContainerRef.current) {
                const containerRect = horizontalContainerRef.current.getBoundingClientRect();
                const containerWidth = containerRect.width;
                const newWidth = containerRect.right - e.clientX;
                const newRatio = newWidth / containerWidth;
                setChartPanelRatio(Math.max(0.25, Math.min(0.75, newRatio))); // Between 25% and 75%
            }
            if (isResizingRepo.current && horizontalContainerRef.current) {
                const containerRect = horizontalContainerRef.current.getBoundingClientRect();
                const containerWidth = containerRect.width;
                const newWidth = e.clientX - containerRect.left;
                const newRatio = newWidth / containerWidth;
                setRepoPanelRatio(Math.max(0.1, Math.min(0.3, newRatio))); // Between 10% and 30%
            }
        };

        const handleMouseUp = () => {
            isResizingVertical.current = false;
            isResizingChart.current = false;
            isResizingRepo.current = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    // Repository file tree
    const { tree: repoTree } = useRepoFileTree(id ?? null);
    const { content: repoFileContent, isLoading: repoFileLoading, loadFile: loadRepoFile } = useRepoFileContent(id ?? null);

    // Compute the set of files modified by the current snapshot
    const modifiedPaths = useMemo(() => {
        if (!fullSnapshot) return new Set<string>();
        const { filename } = parseContentText(fullSnapshot.contentText);
        return filename ? new Set([filename]) : new Set<string>();
    }, [fullSnapshot]);

    // Compute file diffs for comparison mode (shared between tree and panel)
    const comparisonFileDiffs = useMemo(() => {
        if (!comparisonMode || !fullComparisonSnapshot1 || !fullComparisonSnapshot2) return null;
        return computeAllFileDiffs(
            fullComparisonSnapshot1.contentText ?? "",
            fullComparisonSnapshot2.contentText ?? ""
        );
    }, [comparisonMode, fullComparisonSnapshot1, fullComparisonSnapshot2]);

    // Derive per-file change stats for the tree
    const comparisonChangeStats = useMemo(() => {
        if (!comparisonFileDiffs) return undefined;
        const stats = new Map<string, { additions: number; removals: number }>();
        for (const fd of comparisonFileDiffs) {
            if (fd.filename) {
                stats.set(fd.filename, { additions: fd.additions, removals: fd.removals });
            }
        }
        return stats;
    }, [comparisonFileDiffs]);

    const handleSelectRepoFile = (path: string) => {
        setSelectedRepoFile(path);
        if (comparisonMode) {
            // In comparison mode, scroll the diff panel to the clicked file
            setComparisonScrollTarget(path);
            setTimeout(() => setComparisonScrollTarget(null), 200);
            return;
        }
        // If this file is modified by the current snapshot, show the snapshot content
        if (modifiedPaths.has(path) && fullSnapshot) {
            // Show the evolved version from the snapshot
            setShowRepoViewer(false);
        } else {
            // Load from original repo, but keep the snapshot selected
            // so user can click back on the modified file
            loadRepoFile(path);
            setShowRepoViewer(true);
        }
    };

    const handleCloseRepoViewer = () => {
        setShowRepoViewer(false);
        setSelectedRepoFile(null);
    };

    // Determine if multi-objective fitness (more than one fitness key)
    const isMultiObjective = useMemo(() => {
        const fitnessKeys = extractFitnessKeys(snapshots.map((s) => s.fitness));
        return fitnessKeys.length > 1;
    }, [snapshots]);

    // Auto-select point from URL (?point=contentUid) or fallback to best fitness
    const [hasAutoSelected, setHasAutoSelected] = useState(false);
    useEffect(() => {
        if (!DEBUG_ABLATION.autoSelect) return;
        if (!snapshotsLoading && snapshots.length > 0 && !hasAutoSelected && !highlightedSnapshot) {
            const pointFromUrl = searchParams.get("point");

            if (pointFromUrl) {
                // Find snapshot matching the URL point parameter
                const urlSnapshot = snapshotUidMap.get(pointFromUrl);
                if (urlSnapshot) {
                    handleViewCode(urlSnapshot);
                    setHasAutoSelected(true);
                    return;
                }
            }

            // Fallback: find the snapshot with the highest fitness value
            let bestSnapshot = snapshots[0];
            let bestFitness = getFitnessValue(bestSnapshot.fitness);

            for (const snapshot of snapshots) {
                const fitness = getFitnessValue(snapshot.fitness);
                if (fitness > bestFitness) {
                    bestFitness = fitness;
                    bestSnapshot = snapshot;
                }
            }

            // Auto-select the best point
            handleViewCode(bestSnapshot);
            setHasAutoSelected(true);
        }
    }, [snapshotsLoading, snapshots, hasAutoSelected, highlightedSnapshot]);

    // Fetch full content for comparison snapshots when they are selected
    useEffect(() => {
        const fetchComparisonContent = async () => {
            if (comparisonSnapshot1) {
                const { fetchContentSnapshot } = await import("../../lib/graphql-client");
                const full = await fetchContentSnapshot(comparisonSnapshot1.id);
                setFullComparisonSnapshot1(full);
            } else {
                setFullComparisonSnapshot1(null);
            }
        };
        fetchComparisonContent();
    }, [comparisonSnapshot1]);

    useEffect(() => {
        const fetchComparisonContent = async () => {
            if (comparisonSnapshot2) {
                const { fetchContentSnapshot } = await import("../../lib/graphql-client");
                const full = await fetchContentSnapshot(comparisonSnapshot2.id);
                setFullComparisonSnapshot2(full);
            } else {
                setFullComparisonSnapshot2(null);
            }
        };
        fetchComparisonContent();
    }, [comparisonSnapshot2]);

    useEffect(() => {
        if (experiment) {
            setExperimentId(experiment.id);
            setExperimentName(experiment.name ?? null);
        }
        return () => {
            setExperimentName(null);
            setSelectedPointName(null);
            setChartPanelMode("results");
        };
    }, [experiment, setExperimentId, setExperimentName, setSelectedPointName, setChartPanelMode]);

    // When a snapshot is loaded, extract filename and highlight it in repo tree
    useEffect(() => {
        if (fullSnapshot && !showRepoViewer) {
            const { filename } = parseContentText(fullSnapshot.contentText);
            if (filename) {
                setSelectedRepoFile(filename);
            }
            // Update selected point name in header
            setSelectedPointName(fullSnapshot.contentUid.substring(0, 8));
        }
    }, [fullSnapshot, showRepoViewer, setSelectedPointName]);

    const handleViewCode = useCallback(async (snapshot: ContentSnapshotSummary | null) => {
        if (snapshot === null) {
            // Deselect
            setHighlightedSnapshot(null);
            clearFullSnapshot();
            setLineageUid(null);
            setSelectedRepoFile(null);
            setSelectedPointName(null);
            setSearchParams((prev) => { prev.delete("point"); return prev; }, { replace: true });
            return;
        }
        // Switch from repo viewer mode to snapshot viewer mode
        setShowRepoViewer(false);
        // Highlight this point and its ancestors
        setHighlightedSnapshot(snapshot);
        // Build lineage instantly from already-loaded summary data
        setLineageUid(snapshot.contentUid);
        // Update URL with selected point
        setSearchParams((prev) => { prev.set("point", snapshot.contentUid); return prev; }, { replace: true });
        // Only need to fetch the full snapshot content (single API call)
        await loadFullSnapshot(snapshot.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [loadFullSnapshot, clearFullSnapshot, setSearchParams, setSelectedPointName]);

    const handleViewLineage = (snapshot: ContentSnapshotSummary) => {
        if (snapshot.contentUid) {
            setLineageUid(snapshot.contentUid);
            setShowLineageModal(true);
        }
    };

    // Handle clicking on a snapshot UID in the chat
    const handleChatSnapshotClick = useCallback((partialUid: string) => {
        // Find the snapshot that starts with this partial UID
        const snapshot = snapshots.find((s) =>
            s.contentUid.toLowerCase().startsWith(partialUid.toLowerCase())
        );
        if (snapshot) {
            handleViewCode(snapshot);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [snapshots]);

    const handleCloseLineageModal = () => {
        setShowLineageModal(false);
    };

    const handleCloseCodeViewer = () => {
        clearFullSnapshot();
        setHighlightedSnapshot(null); // Clear highlighting
        setLineageUid(null); // Clear lineage display
        setSelectedPointName(null);
    };

    const handleSelectForComparison = useCallback((snapshot: ContentSnapshotSummary) => {
        if (!comparisonSnapshot1) {
            setComparisonSnapshot1(snapshot);
        } else if (!comparisonSnapshot2) {
            // Ensure earlier snapshot is on the left, later on the right
            const time1 = new Date(comparisonSnapshot1.createdAt).getTime();
            const time2 = new Date(snapshot.createdAt).getTime();
            if (time2 < time1) {
                setComparisonSnapshot2(comparisonSnapshot1);
                setComparisonSnapshot1(snapshot);
            } else {
                setComparisonSnapshot2(snapshot);
            }
        } else {
            // Reset and start over
            setComparisonSnapshot1(snapshot);
            setComparisonSnapshot2(null);
        }
    }, [comparisonSnapshot1, comparisonSnapshot2]);

    const findSeedSnapshot = (snapshot: ContentSnapshotSummary): ContentSnapshotSummary | null => {
        let current = snapshot;
        while (current.parentUid) {
            const parent = snapshotUidMap.get(current.parentUid);
            if (!parent) break;
            current = parent;
        }
        return current.contentUid === snapshot.contentUid ? null : current;
    };

    const handleCompareWithParent = () => {
        const selected = comparisonSnapshot1;
        if (!selected?.parentUid) return;
        const parent = snapshotUidMap.get(selected.parentUid);
        if (!parent) return;
        // Parent is always earlier
        setComparisonSnapshot1(parent);
        setComparisonSnapshot2(selected);
    };

    const handleCompareWithSeed = () => {
        const selected = comparisonSnapshot1;
        if (!selected) return;
        const seed = findSeedSnapshot(selected);
        if (!seed) return;
        // Seed is always earlier
        setComparisonSnapshot1(seed);
        setComparisonSnapshot2(selected);
    };

    const handleToggleComparisonMode = () => {
        setComparisonMode(!comparisonMode);
        if (comparisonMode) {
            // Clear selections when exiting comparison mode
            setComparisonSnapshot1(null);
            setComparisonSnapshot2(null);
            setFullComparisonSnapshot1(null);
            setFullComparisonSnapshot2(null);
            setShowOnlyChangedFiles(false);
        } else {
            // Pre-select the currently viewed snapshot as the first comparison target
            if (highlightedSnapshot) {
                setComparisonSnapshot1(highlightedSnapshot);
            }
        }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col" style={{ height: 'calc(100vh - 56px)' }}>
                <div className="flex flex-1 min-h-0 overflow-hidden">
                    {/* Skeleton: repo tree */}
                    <div className="w-[15%] min-w-[120px] border-r p-3 space-y-2">
                        <div className="h-3 w-20 bg-muted animate-pulse rounded" />
                        <div className="space-y-1.5">
                            {[75, 60, 85, 70, 90, 65].map((w, i) => (
                                <div key={i} className="h-3 bg-muted animate-pulse rounded" style={{ width: `${w}%` }} />
                            ))}
                        </div>
                    </div>
                    {/* Skeleton: code viewer */}
                    <div className="flex-1 border-r p-3 space-y-2">
                        <div className="h-3 w-32 bg-muted animate-pulse rounded" />
                        <div className="space-y-1.5">
                            {[80, 55, 70, 90, 45, 85, 60, 75, 50, 65, 80, 70].map((w, i) => (
                                <div key={i} className="h-3 bg-muted animate-pulse rounded" style={{ width: `${w}%` }} />
                            ))}
                        </div>
                    </div>
                    {/* Skeleton: chart panel */}
                    <div className="w-[55%] min-w-[300px] p-3 space-y-2">
                        <div className="h-3 w-24 bg-muted animate-pulse rounded" />
                        <div className="h-full bg-muted/30 animate-pulse rounded" />
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <Card className="border-destructive bg-destructive/10">
                    <CardContent className="pt-6">
                        <p className="text-destructive">Error: {error.message}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!experiment) {
        return (
            <div className="p-6">
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-muted-foreground">Experiment not found.</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex flex-col" style={{ height: '100vh' }}>
            {/* Content Section */}
            {chartPanelMode === "metrics" ? (
                <div className="flex-1 min-h-0">
                    <MetricsTree experimentId={id!} isOngoing={isOngoing} experimentCreatedAt={experiment.createdAt} selectedPaths={selectedMetricPaths} onSelectedPathsChange={setSelectedMetricPaths} />
                </div>
            ) : (
                <>
                    {/* Repository Tree + Code Viewer + Chart Layout */}
                    <Card ref={horizontalContainerRef} className="flex flex-1 min-h-0 overflow-hidden rounded-none border-0">
                        {/* Repository File Tree - Left Panel */}
                        {DEBUG_ABLATION.repoTree && repoTree?.exists && repoTree.root && (
                            <>
                                <div
                                    className="min-w-[120px] flex flex-col border-r"
                                    style={{ flex: `${repoPanelRatio} 1 0%` }}
                                >
                                    <CardHeader className="py-2 px-3 flex-shrink-0 flex flex-row items-center justify-between">
                                        <CardTitle className="text-xs font-medium text-muted-foreground">Repository</CardTitle>
                                        {comparisonMode && comparisonChangeStats && comparisonChangeStats.size > 0 && (
                                            <Button
                                                variant={showOnlyChangedFiles ? "default" : "ghost"}
                                                size="icon"
                                                className="h-5 w-5"
                                                onClick={() => setShowOnlyChangedFiles(!showOnlyChangedFiles)}
                                                title={showOnlyChangedFiles ? "Show all files" : "Show only changed files"}
                                            >
                                                <Filter className="h-3 w-3" />
                                            </Button>
                                        )}
                                    </CardHeader>
                                    <CardContent className="p-0 overflow-auto flex-1 min-h-0">
                                        <FileTree
                                            root={repoTree.root}
                                            selectedPath={selectedRepoFile}
                                            onSelectFile={handleSelectRepoFile}
                                            modifiedPaths={comparisonMode ? undefined : modifiedPaths}
                                            changeStats={comparisonMode ? comparisonChangeStats : undefined}
                                            showOnlyChanged={comparisonMode && showOnlyChangedFiles}
                                        />
                                    </CardContent>
                                </div>
                                {/* Drag handle between repo and code */}
                                <div
                                    className="w-1 cursor-col-resize flex items-center justify-center hover:bg-muted/50 flex-shrink-0"
                                    onMouseDown={handleRepoResizeStart}
                                />
                            </>
                        )}

                        {/* Code Viewer - Middle Panel (shows repo file, evolution chart selection, OR comparison) */}
                        <div
                            className="min-w-[200px] flex flex-col border-r"
                            style={{ flex: `${1 - chartPanelRatio - (repoTree?.exists ? repoPanelRatio : 0)} 1 0%` }}
                        >
                            <CardHeader className="flex flex-row items-center justify-between py-1.5 px-3 flex-shrink-0">
                                {comparisonMode ? (
                                    <CardTitle className="text-xs font-medium text-muted-foreground">
                                        Comparison {comparisonSnapshot1 && comparisonSnapshot2 ? "" : "(select 2)"}
                                    </CardTitle>
                                ) : showRepoViewer && selectedRepoFile ? (
                                    <>
                                        <CardTitle className="text-xs font-medium truncate" title={selectedRepoFile}>
                                            {selectedRepoFile}
                                        </CardTitle>
                                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCloseRepoViewer}>
                                            <span className="text-xs">✕</span>
                                        </Button>
                                    </>
                                ) : highlightedSnapshot && fullSnapshot ? (
                                    (() => {
                                        const { filename } = parseContentText(fullSnapshot.contentText);
                                        return (
                                            <>
                                                <CardTitle className="text-xs font-medium truncate" title={filename || fullSnapshot.contentUid}>
                                                    {filename || fullSnapshot.contentUid.substring(0, 12)} <span className="text-muted-foreground font-normal">• v{fullSnapshot.contentUid.substring(0, 8)}</span>
                                                </CardTitle>
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCloseCodeViewer}>
                                                    <span className="text-xs">✕</span>
                                                </Button>
                                            </>
                                        );
                                    })()
                                ) : (
                                    <CardTitle className="text-xs font-medium text-muted-foreground">
                                        Select a file or point
                                    </CardTitle>
                                )}
                            </CardHeader>
                            <CardContent className="p-0 flex-1 min-h-0">
                                <div className="h-full overflow-auto">
                                    {comparisonMode ? (
                                        <ContentComparisonPanel
                                            snapshot1={fullComparisonSnapshot1}
                                            snapshot2={fullComparisonSnapshot2}
                                            onCompareWithParent={comparisonSnapshot1?.parentUid ? handleCompareWithParent : undefined}
                                            onCompareWithSeed={comparisonSnapshot1 && findSeedSnapshot(comparisonSnapshot1) ? handleCompareWithSeed : undefined}
                                            externalFileDiffs={comparisonFileDiffs ?? undefined}
                                            scrollToFile={comparisonScrollTarget}
                                            onFileSelect={setSelectedRepoFile}
                                        />
                                    ) : showRepoViewer && selectedRepoFile ? (
                                        <FileViewer
                                            content={repoFileContent}
                                            isLoading={repoFileLoading}
                                        />
                                    ) : highlightedSnapshot && fullSnapshot ? (
                                        DEBUG_ABLATION.codeViewer ? (
                                            <MemoizedCodeViewer
                                                contentText={fullSnapshot.contentText}
                                                language={fullSnapshot.language || "python"}
                                            />
                                        ) : (
                                            <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/30">
                                                <p className="text-sm">Code viewer disabled</p>
                                            </div>
                                        )
                                    ) : snapshotLoading ? (
                                        <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/30">
                                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2" />
                                            <p className="text-sm">Loading content...</p>
                                        </div>
                                    ) : (
                                        <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/30">
                                            <p className="text-sm">No code selected</p>
                                        </div>
                                    )}
                                </div>
                            </CardContent>

                            {/* Inline Chat at bottom of code panel */}
                            {id && DEBUG_ABLATION.chatPanel && (
                                <ChatInline
                                    experimentId={id}
                                    isExpanded={showChatPanel}
                                    onToggle={() => setShowChatPanel(!showChatPanel)}
                                    onSnapshotClick={handleChatSnapshotClick}
                                />
                            )}
                        </div>

                        {/* Horizontal drag handle between code and chart */}
                        <div
                            className="w-1 cursor-col-resize flex items-center justify-center hover:bg-muted/50 flex-shrink-0"
                            onMouseDown={handleChartResizeStart}
                        />

                        {/* Evolution Chart - Right Panel */}
                        <div
                            className={`flex flex-col ${chartMaximized ? "fixed inset-4 z-50 w-auto rounded-lg border bg-card text-card-foreground shadow-sm" : "min-w-[300px]"}`}
                            style={chartMaximized ? undefined : { flex: `${chartPanelRatio} 1 0%` }}
                        >
                            <CardHeader className="py-1 px-3 flex flex-row items-center justify-between flex-shrink-0">
                                {isMultiObjective ? (
                                    <Select value={chartViewMode} onValueChange={(v) => setChartViewMode(v as ChartViewMode)}>
                                        <SelectTrigger className="w-auto h-6 text-xs font-medium text-muted-foreground border-none shadow-none px-0 gap-1 hover:text-foreground">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="evolution">Evolution</SelectItem>
                                            <SelectItem value="pareto">Pareto</SelectItem>
                                        </SelectContent>
                                    </Select>
                                ) : (
                                    <span className="text-xs font-medium text-muted-foreground">Evolution</span>
                                )}
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant={comparisonMode ? "default" : "ghost"}
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={handleToggleComparisonMode}
                                        title={comparisonMode ? "Exit comparison" : "Compare snapshots"}
                                    >
                                        <GitCompare className="h-3.5 w-3.5" />
                                    </Button>
                                    {isChartZoomed && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={() => zoomResetRef.current?.()}
                                            title="Reset zoom"
                                        >
                                            <RotateCcw className="h-3.5 w-3.5" />
                                        </Button>
                                    )}
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={() => setChartMaximized(!chartMaximized)}
                                        title={chartMaximized ? "Minimize" : "Maximize"}
                                    >
                                        {chartMaximized ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
                                    </Button>
                                    {/* Legend popover */}
                                    <div className="relative group">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                                                                    >
                                            <HelpCircle className="h-3.5 w-3.5" />
                                        </Button>
                                        <div className="absolute top-7 right-0 hidden group-hover:flex flex-col gap-1 bg-popover border rounded-md shadow-md px-3 py-2 text-xs whitespace-nowrap z-50">
                                            <div className="font-medium text-foreground mb-1">Legend</div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full bg-[#121212]" />
                                                <span className="text-muted-foreground">Content</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full bg-[#3fd58b]" />
                                                <span className="text-muted-foreground">{chartViewMode === "pareto" ? "Pareto Optimal" : "Best Over Time"}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full bg-[#3045ff]" />
                                                <span className="text-muted-foreground">{chartViewMode === "pareto" ? "Selected" : "Selected & Lineage"}</span>
                                            </div>
                                            {chartViewMode !== "pareto" && (
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2.5 h-2.5 rounded-full bg-[#b0bae0]" />
                                                    <span className="text-muted-foreground">Co-parents</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-1 flex-1 min-h-0 overflow-hidden">
                                <div ref={containerRef} className="h-full flex flex-col">
                                    {/* Chart - takes remaining space after lineage */}
                                    <div
                                        className="relative min-h-[100px] overflow-hidden"
                                        style={{
                                            flex: !comparisonMode && lineage && lineage.length > 0
                                                ? `${1 - lineagePanelRatio} 1 0%`
                                                : '1 1 0%'
                                        }}
                                    >
                                        {snapshotsLoading && (
                                            <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60">
                                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
                                            </div>
                                        )}
                                        {DEBUG_ABLATION.chart ? (
                                            <ContentEvolutionChart
                                                    snapshots={snapshots as any}
                                                    onPointClick={comparisonMode ? undefined : handleViewCode as any}
                                                    highlightedSnapshot={comparisonMode || !DEBUG_ABLATION.lineageLines ? undefined : deferredHighlightedSnapshot as any}
                                                    selectedSnapshot1={comparisonMode ? comparisonSnapshot1 as any : undefined}
                                                    selectedSnapshot2={comparisonMode ? comparisonSnapshot2 as any : undefined}
                                                    onSelectForComparison={comparisonMode ? handleSelectForComparison as any : undefined}
                                                    activeView={chartViewMode}
                                                    onActiveViewChange={setChartViewMode}
                                                    onZoomChange={setIsChartZoomed}
                                                    zoomResetRef={zoomResetRef}
                                                />
                                            ) : (
                                                <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/30">
                                                    <p className="text-sm">Chart disabled</p>
                                                </div>
                                            )}
                                        </div>
                                        {/* Resizable Lineage / Evaluation panel */}
                                        {DEBUG_ABLATION.lineagePanel && !comparisonMode && lineage && lineage.length > 0 && (
                                            <>
                                                {/* Drag handle */}
                                                <div
                                                    className="h-2 cursor-row-resize flex items-center justify-center hover:bg-muted/50 group flex-shrink-0"
                                                    onMouseDown={handleVerticalResizeStart}
                                                >
                                                    <div className="w-12 h-1 bg-border rounded-full group-hover:bg-muted-foreground/50" />
                                                </div>
                                                {/* Tab bar */}
                                                <div className="flex border-b px-2 flex-shrink-0">
                                                    <button
                                                        className={`px-2 py-1 text-xs font-medium border-b-2 transition-colors ${
                                                            belowChartTab === "history"
                                                                ? "border-foreground text-foreground"
                                                                : "border-transparent text-muted-foreground hover:text-foreground"
                                                        }`}
                                                        onClick={() => setBelowChartTab("history")}
                                                    >
                                                        Evolution History
                                                    </button>
                                                    <button
                                                        className={`px-2 py-1 text-xs font-medium border-b-2 transition-colors ${
                                                            belowChartTab === "evaluation"
                                                                ? "border-foreground text-foreground"
                                                                : "border-transparent text-muted-foreground hover:text-foreground"
                                                        }`}
                                                        onClick={() => setBelowChartTab("evaluation")}
                                                    >
                                                        Evaluation
                                                    </button>
                                                </div>
                                                {/* Panel content */}
                                                <div
                                                    className="overflow-auto min-h-[50px]"
                                                    style={{ flex: `${lineagePanelRatio} 1 0%` }}
                                                >
                                                    {belowChartTab === "history" ? (
                                                        <LineageHistory
                                                            lineage={lineage}
                                                            selectedUid={highlightedSnapshot?.contentUid}
                                                        />
                                                    ) : (
                                                        <div className="p-3">
                                                            <EvaluationResult result={fullSnapshot?.evaluation} />
                                                        </div>
                                                    )}
                                                </div>
                                            </>
                                        )}
                                </div>
                            </CardContent>
                        </div>
                        {/* Backdrop for maximized chart */}
                        <div
                            className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${chartMaximized ? "opacity-100" : "opacity-0 pointer-events-none"}`}
                            onClick={() => setChartMaximized(false)}
                        />
                    </Card>
                </>
            )}

            {/* Lineage Tree Modal */}
            <LineageTree
                lineage={lineage}
                open={showLineageModal}
                onClose={handleCloseLineageModal}
                onViewCode={handleViewCode}
            />
        </div>
    );
}
