import { useState, useMemo, useEffect, type Dispatch, type SetStateAction } from "react";
import { useQueries } from "@tanstack/react-query";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { Badge } from "../ui/badge";
import { ChevronRight, ChevronDown, BarChart3, Activity, Search } from "lucide-react";
import type { Metric } from "../../types";
import { useMetricKeys } from "../../hooks/use-trial-detail";
import { fetchMetricsByKey } from "../../lib/graphql-client";

interface MetricsTreeProps {
    experimentId: string;
    isOngoing?: boolean;
    experimentCreatedAt?: string;
    selectedPaths?: Set<string>;
    onSelectedPathsChange?: Dispatch<SetStateAction<Set<string>>>;
}

interface TreeNode {
    name: string;
    fullPath: string;
    children: Map<string, TreeNode>;
    isLeaf: boolean;
}

const COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

function formatElapsed(ms: number): string {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
}

function formatElapsedAxis(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) return secs > 0 ? `${hours}h${minutes}m${secs}s` : minutes > 0 ? `${hours}h${minutes}m` : `${hours}h`;
    return secs > 0 ? `${minutes}m${secs}s` : `${minutes}m`;
}

function formatTimestamp(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });
}

function makeMetricsTooltip(startTime: number | null) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return function MetricsTooltipContent({ active, payload }: any) {
        if (!active || !payload || payload.length === 0) return null;

        const meta: Record<string, Metric> | undefined = payload[0]?.payload?._meta;
        const elapsedSec: number | undefined = payload[0]?.payload?.elapsed;

        // Pick the first available metric to show shared point-level info
        const firstMeta = meta
            ? Object.values(meta).find((m): m is Metric => !!m)
            : undefined;

        return (
            <div className="rounded-lg border bg-background p-3 shadow-md text-xs max-w-xs">
                <div className="mb-2">
                    <p className="font-semibold">+{formatElapsed((elapsedSec ?? 0) * 1000)}</p>
                    {firstMeta?.createdAt && (
                        <p className="text-muted-foreground">
                            {formatTimestamp(firstMeta.createdAt)}
                        </p>
                    )}
                </div>
                {payload.map((entry: any) => {
                    const m = meta?.[entry.dataKey];
                    return (
                        <div
                            key={entry.dataKey}
                            className="mb-1.5 last:mb-0"
                        >
                            <div className="flex items-center gap-1.5">
                                <span
                                    className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
                                    style={{ backgroundColor: entry.color }}
                                />
                                <span className="font-medium truncate">{entry.name}</span>
                                <span className="ml-auto tabular-nums font-mono">
                                    {entry.value != null ? Number(entry.value).toPrecision(6) : "—"}
                                </span>
                            </div>
                            {m && (
                                <div className="ml-4 mt-0.5 text-muted-foreground space-y-0.5">
                                    {m.step != null && m.step > 0 && (
                                        <div>Logged step: {m.step}</div>
                                    )}
                                    {m.runId && (
                                        <div className="truncate">Run: {m.runId.slice(0, 8)}</div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };
}

function buildTreeFromKeys(keys: string[]): TreeNode {
    const root: TreeNode = {
        name: "root",
        fullPath: "",
        children: new Map(),
        isLeaf: false,
    };

    keys.forEach((key) => {
        const parts = key.split("/");
        let current = root;

        parts.forEach((part, index) => {
            const isLastPart = index === parts.length - 1;
            const fullPath = parts.slice(0, index + 1).join("/");

            if (!current.children.has(part)) {
                current.children.set(part, {
                    name: part,
                    fullPath,
                    children: new Map(),
                    isLeaf: isLastPart,
                });
            }

            current = current.children.get(part)!;
        });
    });

    return root;
}

function getAllLeafPaths(node: TreeNode): string[] {
    const paths: string[] = [];
    if (node.isLeaf) {
        paths.push(node.fullPath);
    }
    for (const child of node.children.values()) {
        paths.push(...getAllLeafPaths(child));
    }
    return paths;
}

function TreeNodeComponent({
    node,
    level = 0,
    selectedPaths,
    onToggleSelect,
    onToggleSelectAll,
}: {
    node: TreeNode;
    level?: number;
    selectedPaths: Set<string>;
    onToggleSelect: (path: string) => void;
    onToggleSelectAll: (paths: string[]) => void;
}) {
    const [isExpanded, setIsExpanded] = useState(false);

    const hasChildren = node.children.size > 0;
    const isSelected = selectedPaths.has(node.fullPath);

    const leafPaths = getAllLeafPaths(node);
    const selectedCount = leafPaths.filter((path) => selectedPaths.has(path)).length;
    const hasSelectedChildren = selectedCount > 0;
    const allChildrenSelected = selectedCount === leafPaths.length && leafPaths.length > 0;

    const handleExpandClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsExpanded(!isExpanded);
    };

    const handleClick = () => {
        if (node.isLeaf) {
            onToggleSelect(node.fullPath);
        } else if (hasChildren) {
            onToggleSelectAll(leafPaths);
        }
    };

    const childNodes = Array.from(node.children.values()).sort((a, b) =>
        a.name.localeCompare(b.name)
    );

    return (
        <div className="select-none">
            <div
                className={`flex items-center gap-2 py-1 px-2 rounded cursor-pointer hover:bg-muted transition-colors ${
                    isSelected || allChildrenSelected
                        ? "bg-primary/10"
                        : hasSelectedChildren
                          ? "bg-primary/5"
                          : ""
                }`}
                style={{ paddingLeft: `${level * 1.5}rem` }}
            >
                {hasChildren ? (
                    <span
                        className="text-muted-foreground hover:text-foreground"
                        onClick={handleExpandClick}
                    >
                        {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                        ) : (
                            <ChevronRight className="h-4 w-4" />
                        )}
                    </span>
                ) : (
                    <span className="w-4" />
                )}

                <div className="flex items-center gap-2 flex-1" onClick={handleClick}>
                    {node.isLeaf ? (
                        <BarChart3
                            className={`h-4 w-4 ${isSelected ? "text-blue-600" : "text-blue-500"}`}
                        />
                    ) : (
                        <Activity
                            className={`h-4 w-4 ${allChildrenSelected ? "text-primary" : "text-muted-foreground"}`}
                        />
                    )}

                    <span
                        className={`text-sm ${node.isLeaf ? "font-medium" : ""} ${allChildrenSelected ? "font-semibold" : ""}`}
                    >
                        {node.name}
                    </span>

                    {!node.isLeaf && leafPaths.length > 0 && (
                        <Badge
                            variant={
                                allChildrenSelected
                                    ? "default"
                                    : hasSelectedChildren
                                      ? "secondary"
                                      : "outline"
                            }
                            className="ml-auto text-xs"
                        >
                            {selectedCount}/{leafPaths.length}
                        </Badge>
                    )}
                </div>
            </div>

            {isExpanded && hasChildren && (
                <div>
                    {childNodes.map((child) => (
                        <TreeNodeComponent
                            key={child.fullPath}
                            node={child}
                            level={level + 1}
                            selectedPaths={selectedPaths}
                            onToggleSelect={onToggleSelect}
                            onToggleSelectAll={onToggleSelectAll}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function MetricsChart({
    experimentId,
    selectedKeys,
    isOngoing,
    experimentCreatedAt,
}: {
    experimentId: string;
    selectedKeys: string[];
    isOngoing?: boolean;
    experimentCreatedAt?: string;
}) {
    const queries = useQueries({
        queries: selectedKeys.map((key) => ({
            queryKey: ["metricsByKey", experimentId, key],
            queryFn: () => fetchMetricsByKey(experimentId, key, 1000),
            retry: 1,
            refetchInterval: isOngoing ? 60_000 : false,
        })),
    });

    const isLoading = queries.some((q) => q.isLoading);
    const loadedData = selectedKeys
        .map((key, idx) => ({
            key,
            metrics: (queries[idx]?.data ?? []) as Metric[],
            loading: queries[idx]?.isLoading ?? true,
            color: COLORS[idx % COLORS.length],
        }))
        .filter((d) => !d.loading && d.metrics.length > 0);

    const trialStartMs = useMemo(
        () => experimentCreatedAt ? new Date(experimentCreatedAt).getTime() : null,
        [experimentCreatedAt],
    );

    const { chartData, startTime } = useMemo(() => {
        if (loadedData.length === 0) return { chartData: [], startTime: null };

        // Use trial createdAt as the reference start time, falling back to
        // the earliest metric timestamp if unavailable.
        let earliest: number | null = trialStartMs;
        if (earliest === null) {
            for (const { metrics } of loadedData) {
                if (metrics.length > 0 && metrics[0].createdAt) {
                    const t = new Date(metrics[0].createdAt).getTime();
                    if (earliest === null || t < earliest) earliest = t;
                }
            }
        }

        // Collect all data points across all series, keyed by their elapsed
        // time in seconds so the x-axis represents wall-clock time.
        const pointsByElapsed = new Map<number, Record<string, unknown>>();

        for (const { key, metrics } of loadedData) {
            for (const m of metrics) {
                if (!m.createdAt) continue;
                const elapsedSec = Math.max(
                    0,
                    Math.round((new Date(m.createdAt).getTime() - (earliest ?? 0)) / 1000),
                );
                let point = pointsByElapsed.get(elapsedSec);
                if (!point) {
                    point = { elapsed: elapsedSec, _meta: {} };
                    pointsByElapsed.set(elapsedSec, point);
                }
                point[key] = m.value ?? null;
                (point._meta as Record<string, Metric>)[key] = m;
            }
        }

        const data = Array.from(pointsByElapsed.values()).sort(
            (a, b) => (a.elapsed as number) - (b.elapsed as number),
        );

        return { chartData: data, startTime: earliest };
    }, [loadedData, trialStartMs]);

    const CustomTooltip = useMemo(() => makeMetricsTooltip(startTime), [startTime]);

    if (isLoading && loadedData.length === 0) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                    dataKey="elapsed"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={formatElapsedAxis}
                    tick={{ fontSize: 11 }}
                    label={{
                        value: "Time since trial started",
                        position: "bottom",
                        offset: 2,
                        style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" },
                    }}
                />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                {loadedData.map(({ key, color }) => (
                    <Line
                        key={key}
                        type="linear"
                        dataKey={key}
                        stroke={color}
                        dot={{ r: 3, fill: color }}
                        activeDot={{ r: 5 }}
                        strokeWidth={2}
                        connectNulls
                        name={key.split("/").pop()}
                    />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}

export default function MetricsTree({ experimentId, isOngoing, experimentCreatedAt, selectedPaths: externalPaths, onSelectedPathsChange }: MetricsTreeProps) {
    const [internalPaths, setInternalPaths] = useState<Set<string>>(new Set());
    const selectedPaths = externalPaths ?? internalPaths;
    const setSelectedPaths = onSelectedPathsChange ?? setInternalPaths;
    const { metricKeys, metricKeysLoading, metricKeysError } = useMetricKeys(experimentId, {
        refetchInterval: isOngoing ? 60_000 : false,
    });

    const tree = useMemo(() => buildTreeFromKeys(metricKeys), [metricKeys]);

    const [regexFilter, setRegexFilter] = useState("");
    const [regexError, setRegexError] = useState(false);

    useEffect(() => {
        if (!regexFilter) {
            setRegexError(false);
            return;
        }
        try {
            const re = new RegExp(regexFilter);
            setRegexError(false);
            const matched = metricKeys.filter((key) => re.test(key));
            setSelectedPaths(new Set(matched));
        } catch {
            setRegexError(true);
        }
    }, [regexFilter, metricKeys, setSelectedPaths]);

    const handleToggleSelect = (path: string) => {
        setSelectedPaths((prev) => {
            const next = new Set(prev);
            if (next.has(path)) {
                next.delete(path);
            } else {
                next.add(path);
            }
            return next;
        });
    };

    const handleToggleSelectAll = (paths: string[]) => {
        setSelectedPaths((prev) => {
            const next = new Set(prev);
            const allSelected = paths.every((path) => next.has(path));
            if (allSelected) {
                paths.forEach((path) => next.delete(path));
            } else {
                paths.forEach((path) => next.add(path));
            }
            return next;
        });
    };

    const selectedKeys = Array.from(selectedPaths);

    if (metricKeysLoading) {
        return (
            <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
        );
    }

    if (metricKeysError) {
        return (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <p className="text-sm">Failed to load metrics</p>
                <p className="text-xs mt-1">Make sure the backend server is running</p>
            </div>
        );
    }

    if (metricKeys.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Activity className="w-12 h-12 mb-4" />
                <p className="text-sm">No metrics data available</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Chart area */}
            <div className="flex-1 min-h-0">
                {selectedKeys.length > 0 ? (
                    <div className="h-full flex flex-col">
                        {/* Selected badges */}
                        <div className="flex flex-wrap gap-1.5 px-2 pb-2 flex-shrink-0">
                            {selectedKeys.map((key, idx) => (
                                <Badge
                                    key={key}
                                    variant="secondary"
                                    className="cursor-pointer hover:bg-destructive/20 text-xs"
                                    style={{ borderLeft: `3px solid ${COLORS[idx % COLORS.length]}` }}
                                    onClick={() => handleToggleSelect(key)}
                                >
                                    {key.split("/").pop()} ×
                                </Badge>
                            ))}
                        </div>
                        {/* Chart */}
                        <div className="flex-1 min-h-0">
                            <MetricsChart experimentId={experimentId} selectedKeys={selectedKeys} isOngoing={isOngoing} experimentCreatedAt={experimentCreatedAt} />
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        <div className="text-center">
                            <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p className="text-sm">Select metrics from below to visualize</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Bottom panels */}
            <div className="border-t flex-shrink-0 max-h-[40%] flex">
                {/* Tree browser */}
                <div className="flex-1 overflow-y-auto min-w-0">
                    <div className="px-3 py-2 border-b bg-muted/30">
                        <p className="text-xs font-medium text-muted-foreground">
                            Metrics Browser
                            <span className="ml-1.5 text-foreground">{metricKeys.length} metric{metricKeys.length !== 1 ? "s" : ""}</span>
                        </p>
                    </div>
                    <div className="py-1">
                        {Array.from(tree.children.values()).map((child) => (
                            <TreeNodeComponent
                                key={child.fullPath}
                                node={child}
                                level={0}
                                selectedPaths={selectedPaths}
                                onToggleSelect={handleToggleSelect}
                                onToggleSelectAll={handleToggleSelectAll}
                            />
                        ))}
                    </div>
                </div>

                {/* Regex filter panel */}
                <div className="w-64 border-l overflow-y-auto flex-shrink-0">
                    <div className="px-3 py-2 border-b bg-muted/30">
                        <p className="text-xs font-medium text-muted-foreground">Regex Select</p>
                    </div>
                    <div className="p-3 space-y-2">
                        <div className="relative">
                            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                            <input
                                type="text"
                                value={regexFilter}
                                onChange={(e) => setRegexFilter(e.target.value)}
                                placeholder="e.g. loss|accuracy"
                                className={`w-full pl-7 pr-2 py-1 text-xs rounded border bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 ${
                                    regexError
                                        ? "border-destructive focus:ring-destructive"
                                        : "border-input focus:ring-ring"
                                }`}
                            />
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                            Matches select metrics automatically
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
