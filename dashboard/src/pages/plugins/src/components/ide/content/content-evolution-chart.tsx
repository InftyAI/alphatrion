import { useMemo, useState, useCallback, useRef, useEffect, memo } from "react";
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Line,
} from "recharts";
import { Badge } from "../ui/badge";
import { Code } from "lucide-react";
import type { ContentSnapshot } from "../../types";
import {
    formatFitness,
    extractFitnessKeys,
    getFitnessValueForKey,
    getKeyDisplayName,
    isMultiObjectiveFitness,
    evaluateWeightedAverage,
    createInitialWeights,
    computeParetoFrontier,
} from "../../utils/fitness";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "../ui/select";

export type ChartViewMode = "evolution" | "pareto";

interface ContentEvolutionChartProps {
    snapshots: ContentSnapshot[];
    onPointClick?: (snapshot: ContentSnapshot | null) => void;
    selectedSnapshot1?: ContentSnapshot | null;
    selectedSnapshot2?: ContentSnapshot | null;
    onSelectForComparison?: (snapshot: ContentSnapshot) => void;
    highlightedSnapshot?: ContentSnapshot | null;
    onLineageChange?: (lineage: ContentSnapshot[]) => void;
    activeView?: ChartViewMode;
    onActiveViewChange?: (view: ChartViewMode) => void;
    onZoomChange?: (isZoomed: boolean) => void;
    zoomResetRef?: React.MutableRefObject<(() => void) | null>;
}

interface ChartPoint {
    timestamp: number;
    fitness: number;
    snapshot: ContentSnapshot;
    label: string;
    isSeed: boolean;
}

function ContentEvolutionChartInner({
    snapshots,
    onPointClick,
    selectedSnapshot1,
    selectedSnapshot2,
    onSelectForComparison,
    highlightedSnapshot,
    onLineageChange,
    activeView: controlledActiveView,
    onActiveViewChange,
    onZoomChange,
    zoomResetRef,
}: ContentEvolutionChartProps) {
    const isComparisonMode = !!onSelectForComparison;

    // Extract all unique fitness keys for multi-objective
    const fitnessKeys = useMemo(
        () => extractFitnessKeys(snapshots.map((s) => s.fitness)),
        [snapshots]
    );

    const isMultiObjective = fitnessKeys.length > 1;

    // Use controlled view if provided, otherwise internal state
    const [internalActiveTab] = useState<ChartViewMode>("evolution");
    const activeTab = controlledActiveView ?? internalActiveTab;

    const [selectedFitnessKey, setSelectedFitnessKey] = useState<string | null>(null);
    const [showWeightsPopover, setShowWeightsPopover] = useState(false);
    const [weights, setWeights] = useState<Record<string, number>>(() =>
        createInitialWeights(fitnessKeys)
    );
    // Separate weights for Pareto X and Y axes
    const [paretoXWeights, setParetoXWeights] = useState<Record<string, number>>(() =>
        createInitialWeights(fitnessKeys)
    );
    const [paretoYWeights, setParetoYWeights] = useState<Record<string, number>>(() =>
        createInitialWeights(fitnessKeys)
    );

    // Pareto frontier axis selection
    const [paretoXAxis, setParetoXAxis] = useState<string | null>(null);
    const [paretoYAxis, setParetoYAxis] = useState<string | null>(null);

    // Box-selection zoom state for evolution chart
    const [evolutionZoom, setEvolutionZoom] = useState<{
        x: [number, number];
        y: [number, number];
    } | null>(null);
    // Selection box in pixel coordinates (relative to container)
    const [evolutionSelectionPx, setEvolutionSelectionPx] = useState<{
        x1: number;
        y1: number;
        x2: number;
        y2: number;
    } | null>(null);
    const isSelectingEvolution = useRef(false);
    const evolutionDragStart = useRef<{ x: number; y: number } | null>(null);

    // Box-selection zoom state for pareto chart
    const [paretoZoom, setParetoZoom] = useState<{
        x: [number, number];
        y: [number, number];
    } | null>(null);
    // Selection box in pixel coordinates (relative to container)
    const [paretoSelectionPx, setParetoSelectionPx] = useState<{
        x1: number;
        y1: number;
        x2: number;
        y2: number;
    } | null>(null);
    const isSelectingPareto = useRef(false);
    const paretoDragStart = useRef<{ x: number; y: number } | null>(null);

    // Chart margins (must match what's passed to ScatterChart)
    const chartMargin = { top: 10, right: 10, bottom: 30, left: 5 };

    // Initialize Pareto axes when fitness keys become available
    useMemo(() => {
        if (fitnessKeys.length >= 2) {
            if (!paretoXAxis || !fitnessKeys.includes(paretoXAxis)) {
                setParetoXAxis(fitnessKeys[0]);
            }
            if (!paretoYAxis || !fitnessKeys.includes(paretoYAxis)) {
                setParetoYAxis(fitnessKeys[1]);
            }
        }
    }, [fitnessKeys]);

    // Update weights when fitnessKeys change
    useMemo(() => {
        setWeights((prev) => {
            const newWeights = { ...prev };
            for (const key of fitnessKeys) {
                if (!(key in newWeights)) {
                    newWeights[key] = 1;
                }
            }
            return newWeights;
        });
    }, [fitnessKeys]);

    const isWeightedMode = selectedFitnessKey === "__weighted__";

    // Use selected key or first available key (null if weighted mode)
    const activeFitnessKey = isWeightedMode
        ? null
        : (selectedFitnessKey ?? fitnessKeys[0] ?? null);

    const updateWeight = (key: string, value: number) => {
        setWeights((prev) => ({
            ...prev,
            [key]: Math.max(0, value),
        }));
    };

    const updateParetoXWeight = (key: string, value: number) => {
        setParetoXWeights((prev) => ({
            ...prev,
            [key]: Math.max(0, value),
        }));
    };

    const updateParetoYWeight = (key: string, value: number) => {
        setParetoYWeights((prev) => ({
            ...prev,
            [key]: Math.max(0, value),
        }));
    };

    // Popover states for Pareto custom weights
    const [showParetoXWeightsPopover, setShowParetoXWeightsPopover] = useState(false);
    const [showParetoYWeightsPopover, setShowParetoYWeightsPopover] = useState(false);

    const chartData = useMemo(() => {
        // Find the earliest timestamp to use as the baseline
        const timestamps = snapshots.map((s) => new Date(s.createdAt).getTime());
        const minTimestamp = timestamps.length > 0 ? Math.min(...timestamps) : 0;

        return snapshots.map((snapshot): ChartPoint => {
            const absoluteTimestamp = new Date(snapshot.createdAt).getTime();
            const timestamp = absoluteTimestamp - minTimestamp; // Relative time from start

            let fitness: number;
            if (isWeightedMode && isMultiObjectiveFitness(snapshot.fitness)) {
                fitness = evaluateWeightedAverage(snapshot.fitness, weights);
            } else {
                fitness = getFitnessValueForKey(snapshot.fitness, activeFitnessKey);
            }

            return {
                timestamp,
                fitness,
                snapshot,
                label: snapshot.contentUid.substring(0, 8),
                isSeed: !snapshot.parentUid,
            };
        });
    }, [snapshots, activeFitnessKey, isWeightedMode, weights]);

    // Compute "best over time" frontier - shows the running maximum fitness over time
    const { bestOverTimeLine, bestPointUids } = useMemo(() => {
        if (chartData.length === 0) return { bestOverTimeLine: [], bestPointUids: new Set<string>() };

        // Sort by timestamp
        const sorted = [...chartData].sort((a, b) => a.timestamp - b.timestamp);

        const frontier: Array<{ timestamp: number; fitness: number }> = [];
        const bestUids = new Set<string>();
        let bestSoFar = -Infinity;

        for (const point of sorted) {
            if (point.fitness > bestSoFar) {
                bestSoFar = point.fitness;
                frontier.push({ timestamp: point.timestamp, fitness: point.fitness });
                bestUids.add(point.snapshot.contentUid);
            }
        }

        // Add a final point at the last timestamp to extend the line
        if (frontier.length > 0 && sorted.length > 0) {
            const lastTimestamp = sorted[sorted.length - 1].timestamp;
            const lastFrontierPoint = frontier[frontier.length - 1];
            if (lastFrontierPoint.timestamp < lastTimestamp) {
                frontier.push({ timestamp: lastTimestamp, fitness: lastFrontierPoint.fitness });
            }
        }

        return { bestOverTimeLine: frontier, bestPointUids: bestUids };
    }, [chartData]);

    // Pareto frontier data for scatter plot
    interface ParetoPoint {
        x: number;
        y: number;
        snapshot: ContentSnapshot;
        label: string;
        isPareto: boolean;
        isSeed: boolean;
    }

    // Check if pareto axes are in weighted mode
    const isParetoXWeighted = paretoXAxis === "__weighted__";
    const isParetoYWeighted = paretoYAxis === "__weighted__";

    // Get the actual fitness value for a pareto axis (handles custom/weighted mode)
    const getParetoAxisValue = (fitness: Record<string, number>, axis: string | null, isCustom: boolean, axisWeights: Record<string, number>) => {
        if (isCustom) {
            return evaluateWeightedAverage(fitness, axisWeights);
        }
        return axis ? (fitness[axis] ?? 0) : 0;
    };

    const paretoData = useMemo(() => {
        if (!isMultiObjective || !paretoXAxis || !paretoYAxis) {
            return { allPoints: [], paretoPoints: [], frontierLine: [] };
        }

        // Filter snapshots that have multi-objective fitness
        const multiObjSnapshots = snapshots.filter((s) =>
            isMultiObjectiveFitness(s.fitness)
        );

        // For Pareto frontier computation, use actual keys (not weighted)
        const effectiveXAxis = isParetoXWeighted ? null : paretoXAxis;
        const effectiveYAxis = isParetoYWeighted ? null : paretoYAxis;

        let paretoSet = new Set<string>();
        if (effectiveXAxis && effectiveYAxis) {
            const paretoOptimal = computeParetoFrontier(
                multiObjSnapshots,
                (s) => s.fitness as Record<string, number>,
                [effectiveXAxis, effectiveYAxis],
                true // maximize
            );
            paretoSet = new Set(paretoOptimal.map((s) => s.contentUid));
        }

        const allPoints: ParetoPoint[] = multiObjSnapshots.map((snapshot) => {
            const fitness = snapshot.fitness as Record<string, number>;
            return {
                x: getParetoAxisValue(fitness, paretoXAxis, isParetoXWeighted, paretoXWeights),
                y: getParetoAxisValue(fitness, paretoYAxis, isParetoYWeighted, paretoYWeights),
                snapshot,
                label: snapshot.contentUid.substring(0, 8),
                isPareto: paretoSet.has(snapshot.contentUid),
                isSeed: !snapshot.parentUid,
            };
        });

        const paretoPoints = allPoints.filter((p) => p.isPareto);

        // Sort Pareto points by x for drawing the frontier line
        const frontierLine = [...paretoPoints].sort((a, b) => a.x - b.x);

        return { allPoints, paretoPoints, frontierLine };
    }, [snapshots, isMultiObjective, paretoXAxis, paretoYAxis, isParetoXWeighted, isParetoYWeighted, paretoXWeights, paretoYWeights]);

    const formatTimestamp = (timestamp: number) => {
        // timestamp is now relative time in milliseconds from start
        const totalSeconds = Math.floor(timestamp / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        } else {
            return `${seconds}s`;
        }
    };

    // Build a map of contentUid to chart point for lineage rendering
    const contentUidToPoint = useMemo(() => {
        const map = new Map<string, ChartPoint>();
        chartData.forEach(point => {
            map.set(point.snapshot.contentUid, point);
        });
        return map;
    }, [chartData]);

    // Get parent ancestors, co-parent ancestors, and ordered lineage for highlighted snapshot
    // Build a uid→snapshot lookup map once (O(n)), used for all lineage traversals
    const snapshotUidMap = useMemo(() => {
        const map = new Map<string, ContentSnapshot>();
        for (const s of snapshots) {
            map.set(s.contentUid, s);
        }
        return map;
    }, [snapshots]);

    const { parentAncestors, coParentAncestors, lineageSnapshots } = useMemo(() => {
        if (!highlightedSnapshot) {
            return { parentAncestors: new Set<string>(), coParentAncestors: new Set<string>(), lineageSnapshots: [] };
        }

        const parents = new Set<string>();
        const coParents = new Set<string>();
        const lineage: ContentSnapshot[] = [];
        const visited = new Set<string>();

        const collectParentLineage = (snap: ContentSnapshot) => {
            if (visited.has(snap.contentUid)) return;
            visited.add(snap.contentUid);

            lineage.push(snap);

            if (snap.coParentUids) {
                snap.coParentUids.forEach(coParentUid => {
                    coParents.add(coParentUid);
                });
            }

            if (snap.parentUid) {
                parents.add(snap.parentUid);
                const parent = snapshotUidMap.get(snap.parentUid);
                if (parent) collectParentLineage(parent);
            }
        };

        collectParentLineage(highlightedSnapshot);
        lineage.reverse();
        return { parentAncestors: parents, coParentAncestors: coParents, lineageSnapshots: lineage };
    }, [highlightedSnapshot, snapshotUidMap]);

    // Notify parent component when lineage changes
    useEffect(() => {
        onLineageChange?.(lineageSnapshots);
    }, [lineageSnapshots, onLineageChange]);

    // Generic function to compute lineage lines given a coordinate getter
    // Main parent lineage is shown in the primary color, co-parents shown in secondary color (no recursion)
    // Returns { parentLines, coParentLines } so they can be rendered in correct z-order
    const computeLineageLines = useCallback((
        targetSnapshots: Array<{ snapshot: ContentSnapshot | null | undefined; color: string; coParentColor: string }>,
        getCoords: (contentUid: string) => { x: number; y: number } | null
    ) => {
        const parentLines: Array<{ x1: number; y1: number; x2: number; y2: number; color: string }> = [];
        const coParentLines: Array<{ x1: number; y1: number; x2: number; y2: number; color: string }> = [];

        const addLinesForSnapshot = (snapshot: ContentSnapshot | null | undefined, color: string, coParentColor: string) => {
            if (!snapshot) return;

            const visited = new Set<string>();

            const addLines = (snap: ContentSnapshot) => {
                if (visited.has(snap.contentUid)) return;
                visited.add(snap.contentUid);

                const childCoords = getCoords(snap.contentUid);
                if (!childCoords) return;

                // Draw line to parent (and recurse)
                if (snap.parentUid) {
                    const parentCoords = getCoords(snap.parentUid);
                    if (parentCoords) {
                        parentLines.push({
                            x1: parentCoords.x,
                            y1: parentCoords.y,
                            x2: childCoords.x,
                            y2: childCoords.y,
                            color: color,
                        });
                        const parentSnapshot = snapshotUidMap.get(snap.parentUid);
                        if (parentSnapshot) addLines(parentSnapshot);
                    }
                }

                // Draw lines to co-parents (NO recursion, different color)
                if (snap.coParentUids) {
                    (snap.coParentUids as string[]).forEach((coParentUid: string) => {
                        const coParentCoords = getCoords(coParentUid);
                        if (coParentCoords) {
                            coParentLines.push({
                                x1: coParentCoords.x,
                                y1: coParentCoords.y,
                                x2: childCoords.x,
                                y2: childCoords.y,
                                color: coParentColor,
                            });
                            // Don't recurse on co-parents
                        }
                    });
                }
            };

            addLines(snapshot);
        };

        targetSnapshots.forEach(({ snapshot, color, coParentColor }) => {
            addLinesForSnapshot(snapshot, color, coParentColor);
        });

        return { parentLines, coParentLines };
    }, [snapshotUidMap]);

    // Helper to generate nice round tick values
    const generateNiceTicks = (min: number, max: number, targetCount: number = 5): number[] => {
        const range = max - min;
        if (range === 0) return [min];

        // Find a nice step size
        const roughStep = range / targetCount;
        const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
        const residual = roughStep / magnitude;

        let niceStep: number;
        if (residual <= 1) niceStep = magnitude;
        else if (residual <= 2) niceStep = 2 * magnitude;
        else if (residual <= 5) niceStep = 5 * magnitude;
        else niceStep = 10 * magnitude;

        // Generate ticks
        const ticks: number[] = [];
        const start = Math.ceil(min / niceStep) * niceStep;
        for (let tick = start; tick <= max; tick += niceStep) {
            ticks.push(Math.round(tick * 1e10) / 1e10); // Avoid floating point issues
        }

        // Always include 0 if it's in range
        if (min <= 0 && max >= 0 && !ticks.includes(0)) {
            ticks.push(0);
            ticks.sort((a, b) => a - b);
        }

        return ticks;
    };

    // Helper to generate nice time ticks (in ms)
    const generateNiceTimeTicks = (minMs: number, maxMs: number, targetCount: number = 5): number[] => {
        const range = maxMs - minMs;
        if (range <= 0) return [minMs];

        // Nice time intervals in ms
        const niceIntervals = [
            1000, 2000, 5000, 10000, 15000, 30000, // seconds
            60000, 120000, 300000, 600000, // minutes
            900000, 1800000, 3600000, // 15m, 30m, 1h
        ];

        const roughStep = range / targetCount;
        let step = niceIntervals[0];
        for (const interval of niceIntervals) {
            if (interval >= roughStep) {
                step = interval;
                break;
            }
            step = interval;
        }

        const ticks: number[] = [];
        const start = Math.ceil(minMs / step) * step;
        for (let tick = start; tick <= maxMs; tick += step) {
            ticks.push(tick);
        }

        // Ensure we have at least the start if no ticks generated
        if (ticks.length === 0) {
            ticks.push(minMs);
        }

        return ticks;
    };

    // Compute evolution chart data bounds
    const evolutionBounds = useMemo(() => {
        if (chartData.length === 0) return { xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
        const timestamps = chartData.map(d => d.timestamp);
        const fitnesses = chartData.map(d => d.fitness);
        const xMax = Math.max(...timestamps);
        const yMin = Math.min(...fitnesses);
        const yMax = Math.max(...fitnesses);

        // Small padding for y-axis only
        const yPad = (yMax - yMin) * 0.08 || 0.1;

        return {
            xMin: 0,
            xMax: xMax,
            yMin: yMin - yPad,
            yMax: yMax + yPad,
        };
    }, [chartData]);

    // Compute nice tick values for evolution chart (works for both normal and zoomed)
    const evolutionTicks = useMemo(() => {
        const xDomain = evolutionZoom ? evolutionZoom.x : [evolutionBounds.xMin, evolutionBounds.xMax];
        const yDomain = evolutionZoom ? evolutionZoom.y : [evolutionBounds.yMin, evolutionBounds.yMax];
        const xTicks = generateNiceTimeTicks(xDomain[0], xDomain[1], 5);
        const yTicks = generateNiceTicks(yDomain[0], yDomain[1]);
        return { xTicks, yTicks };
    }, [evolutionBounds, evolutionZoom]);

    // Compute pareto chart data bounds
    const paretoBounds = useMemo(() => {
        if (paretoData.allPoints.length === 0) return { xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
        const xs = paretoData.allPoints.map(d => d.x);
        const ys = paretoData.allPoints.map(d => d.y);
        const xMin = Math.min(...xs);
        const xMax = Math.max(...xs);
        const yMin = Math.min(...ys);
        const yMax = Math.max(...ys);

        // Small padding for visual comfort
        const xPad = (xMax - xMin) * 0.08 || 0.1;
        const yPad = (yMax - yMin) * 0.08 || 0.1;

        return {
            xMin: xMin - xPad,
            xMax: xMax + xPad,
            yMin: yMin - yPad,
            yMax: yMax + yPad,
        };
    }, [paretoData.allPoints]);

    // Compute nice tick values for pareto chart (works for both normal and zoomed)
    const paretoTicks = useMemo(() => {
        const xDomain = paretoZoom ? paretoZoom.x : [paretoBounds.xMin, paretoBounds.xMax];
        const yDomain = paretoZoom ? paretoZoom.y : [paretoBounds.yMin, paretoBounds.yMax];
        const xTicks = generateNiceTicks(xDomain[0], xDomain[1]);
        const yTicks = generateNiceTicks(yDomain[0], yDomain[1]);
        return { xTicks, yTicks };
    }, [paretoBounds, paretoZoom]);

    // Filter chart data to only include points within the current zoom domain
    const filteredChartData = useMemo(() => {
        if (!evolutionZoom) return chartData;
        const [xMin, xMax] = evolutionZoom.x;
        const [yMin, yMax] = evolutionZoom.y;
        return chartData.filter(p =>
            p.timestamp >= xMin && p.timestamp <= xMax &&
            p.fitness >= yMin && p.fitness <= yMax
        );
    }, [chartData, evolutionZoom]);

    // Pre-split scatter data into regular and best-over-time points (avoid .filter() in JSX)
    const { regularPoints, bestPoints } = useMemo(() => {
        const regular: ChartPoint[] = [];
        const best: ChartPoint[] = [];
        for (const p of filteredChartData) {
            if (bestPointUids.has(p.snapshot.contentUid)) {
                best.push(p);
            } else {
                regular.push(p);
            }
        }
        return { regularPoints: regular, bestPoints: best };
    }, [filteredChartData, bestPointUids]);

    // Filter pareto data to only include points within the current zoom domain
    const filteredParetoData = useMemo(() => {
        if (!paretoZoom) return paretoData;
        const [xMin, xMax] = paretoZoom.x;
        const [yMin, yMax] = paretoZoom.y;
        return {
            ...paretoData,
            allPoints: paretoData.allPoints.filter(p =>
                p.x >= xMin && p.x <= xMax &&
                p.y >= yMin && p.y <= yMax
            ),
            paretoPoints: paretoData.paretoPoints.filter(p =>
                p.x >= xMin && p.x <= xMax &&
                p.y >= yMin && p.y <= yMax
            ),
        };
    }, [paretoData, paretoZoom]);

    // Minimum drag distance before starting selection (to allow clicks through)
    const MIN_DRAG_DISTANCE = 5;

    // Track whether we're actively dragging (for conditional event handling)
    const [isDraggingEvolution, setIsDraggingEvolution] = useState(false);
    const [isDraggingPareto, setIsDraggingPareto] = useState(false);

    // Evolution chart zoom handlers
    const evolutionChartRef = useRef<HTMLDivElement>(null);

    const handleEvolutionMouseDown = useCallback((e: React.MouseEvent) => {
        if (!evolutionChartRef.current) return;
        // Don't start drag if clicking on a scatter point (let recharts handle the click)
        const target = e.target as Element;
        if (target.closest('.recharts-symbols') || target.closest('.recharts-scatter-symbol')) {
            return;
        }
        const rect = evolutionChartRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        evolutionDragStart.current = { x, y };
        isSelectingEvolution.current = false;
        setIsDraggingEvolution(true);
    }, []);

    const handleEvolutionMouseMove = useCallback((e: React.MouseEvent) => {
        if (!evolutionDragStart.current || !evolutionChartRef.current) return;

        const rect = evolutionChartRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const dx = x - evolutionDragStart.current.x;
        const dy = y - evolutionDragStart.current.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Only start selection after dragging minimum distance
        if (!isSelectingEvolution.current && distance >= MIN_DRAG_DISTANCE) {
            isSelectingEvolution.current = true;
            setEvolutionSelectionPx({
                x1: evolutionDragStart.current.x,
                y1: evolutionDragStart.current.y,
                x2: evolutionDragStart.current.x,
                y2: evolutionDragStart.current.y,
            });
        }

        if (isSelectingEvolution.current) {
            setEvolutionSelectionPx(prev => prev ? {
                ...prev,
                x2: x,
                y2: y,
            } : null);
        }
    }, []);

    const handleEvolutionMouseUp = useCallback(() => {
        if (isSelectingEvolution.current && evolutionSelectionPx && evolutionChartRef.current) {
            // Find the cartesian grid to get exact plot area position
            const cartesianGrid = evolutionChartRef.current.querySelector('.recharts-cartesian-grid');
            const containerRect = evolutionChartRef.current.getBoundingClientRect();

            if (!cartesianGrid) return;

            const gridRect = cartesianGrid.getBoundingClientRect();

            // The grid rect gives us the exact plot area position
            const plotLeft = gridRect.left - containerRect.left;
            const plotTop = gridRect.top - containerRect.top;
            const plotWidth = gridRect.width;
            const plotHeight = gridRect.height;

            const { x1: rawX1, y1: rawY1, x2: rawX2, y2: rawY2 } = evolutionSelectionPx;

            // Convert selection coordinates to plot-relative coordinates
            const x1 = rawX1 - plotLeft;
            const y1 = rawY1 - plotTop;
            const x2 = rawX2 - plotLeft;
            const y2 = rawY2 - plotTop;

            const xDomain = evolutionZoom ? evolutionZoom.x : [evolutionBounds.xMin, evolutionBounds.xMax];
            const yDomain = evolutionZoom ? evolutionZoom.y : [evolutionBounds.yMin, evolutionBounds.yMax];

            // Convert plot-relative coordinates to data coordinates
            // x1, y1, x2, y2 are already relative to the plot area (cartesian grid)
            const toDataX = (plotX: number) => {
                const clampedX = Math.max(0, Math.min(plotWidth, plotX));
                return xDomain[0] + (clampedX / plotWidth) * (xDomain[1] - xDomain[0]);
            };
            const toDataY = (plotY: number) => {
                const clampedY = Math.max(0, Math.min(plotHeight, plotY));
                return yDomain[1] - (clampedY / plotHeight) * (yDomain[1] - yDomain[0]);
            };

            const dataX1 = toDataX(x1);
            const dataX2 = toDataX(x2);
            const dataY1 = toDataY(y1);
            const dataY2 = toDataY(y2);

            const minX = Math.min(dataX1, dataX2);
            const maxX = Math.max(dataX1, dataX2);
            const minY = Math.min(dataY1, dataY2);
            const maxY = Math.max(dataY1, dataY2);

            // Only zoom if selection is meaningful
            const xRange = xDomain[1] - xDomain[0];
            const yRange = yDomain[1] - yDomain[0];

            if ((maxX - minX) > xRange * 0.02 && (maxY - minY) > yRange * 0.02) {
                setEvolutionZoom({
                    x: [minX, maxX],
                    y: [minY, maxY],
                });
            }
        }
        evolutionDragStart.current = null;
        isSelectingEvolution.current = false;
        setEvolutionSelectionPx(null);
        setIsDraggingEvolution(false);
    }, [evolutionSelectionPx, evolutionBounds, evolutionZoom, chartMargin]);

    const resetEvolutionZoom = useCallback(() => {
        setEvolutionZoom(null);
    }, []);

    // Pareto chart zoom handlers
    const paretoChartRef = useRef<HTMLDivElement>(null);

    const handleParetoMouseDown = useCallback((e: React.MouseEvent) => {
        if (!paretoChartRef.current) return;
        // Don't start drag if clicking on a scatter point (let recharts handle the click)
        const target = e.target as Element;
        if (target.closest('.recharts-symbols') || target.closest('.recharts-scatter-symbol')) {
            return;
        }
        const rect = paretoChartRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        paretoDragStart.current = { x, y };
        isSelectingPareto.current = false;
        setIsDraggingPareto(true);
    }, []);

    const handleParetoMouseMove = useCallback((e: React.MouseEvent) => {
        if (!paretoDragStart.current || !paretoChartRef.current) return;

        const rect = paretoChartRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const dx = x - paretoDragStart.current.x;
        const dy = y - paretoDragStart.current.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Only start selection after dragging minimum distance
        if (!isSelectingPareto.current && distance >= MIN_DRAG_DISTANCE) {
            isSelectingPareto.current = true;
            setParetoSelectionPx({
                x1: paretoDragStart.current.x,
                y1: paretoDragStart.current.y,
                x2: paretoDragStart.current.x,
                y2: paretoDragStart.current.y,
            });
        }

        if (isSelectingPareto.current) {
            setParetoSelectionPx(prev => prev ? {
                ...prev,
                x2: x,
                y2: y,
            } : null);
        }
    }, []);

    const handleParetoMouseUp = useCallback(() => {
        if (isSelectingPareto.current && paretoSelectionPx && paretoChartRef.current) {
            // Find the cartesian grid to get exact plot area position
            const cartesianGrid = paretoChartRef.current.querySelector('.recharts-cartesian-grid');
            const containerRect = paretoChartRef.current.getBoundingClientRect();

            if (!cartesianGrid) return;

            const gridRect = cartesianGrid.getBoundingClientRect();

            // The grid rect gives us the exact plot area position
            const plotLeft = gridRect.left - containerRect.left;
            const plotTop = gridRect.top - containerRect.top;
            const plotWidth = gridRect.width;
            const plotHeight = gridRect.height;

            const { x1: rawX1, y1: rawY1, x2: rawX2, y2: rawY2 } = paretoSelectionPx;

            // Convert selection coordinates to plot-relative coordinates
            const x1 = rawX1 - plotLeft;
            const y1 = rawY1 - plotTop;
            const x2 = rawX2 - plotLeft;
            const y2 = rawY2 - plotTop;

            const xDomain = paretoZoom ? paretoZoom.x : [paretoBounds.xMin, paretoBounds.xMax];
            const yDomain = paretoZoom ? paretoZoom.y : [paretoBounds.yMin, paretoBounds.yMax];

            // Convert plot-relative coordinates to data coordinates
            const toDataX = (plotX: number) => {
                const clampedX = Math.max(0, Math.min(plotWidth, plotX));
                return xDomain[0] + (clampedX / plotWidth) * (xDomain[1] - xDomain[0]);
            };
            const toDataY = (plotY: number) => {
                const clampedY = Math.max(0, Math.min(plotHeight, plotY));
                return yDomain[1] - (clampedY / plotHeight) * (yDomain[1] - yDomain[0]);
            };

            const dataX1 = toDataX(x1);
            const dataX2 = toDataX(x2);
            const dataY1 = toDataY(y1);
            const dataY2 = toDataY(y2);

            const minX = Math.min(dataX1, dataX2);
            const maxX = Math.max(dataX1, dataX2);
            const minY = Math.min(dataY1, dataY2);
            const maxY = Math.max(dataY1, dataY2);

            // Only zoom if selection is meaningful
            const xRange = xDomain[1] - xDomain[0];
            const yRange = yDomain[1] - yDomain[0];

            if ((maxX - minX) > xRange * 0.02 && (maxY - minY) > yRange * 0.02) {
                setParetoZoom({
                    x: [minX, maxX],
                    y: [minY, maxY],
                });
            }
        }
        paretoDragStart.current = null;
        isSelectingPareto.current = false;
        setParetoSelectionPx(null);
        setIsDraggingPareto(false);
    }, [paretoSelectionPx, paretoBounds, paretoZoom, chartMargin]);

    const resetParetoZoom = useCallback(() => {
        setParetoZoom(null);
    }, []);

    // Expose zoom state and reset function to parent
    const isZoomed = activeTab === "pareto" ? !!paretoZoom : !!evolutionZoom;
    const resetZoom = activeTab === "pareto" ? resetParetoZoom : resetEvolutionZoom;

    useEffect(() => {
        onZoomChange?.(isZoomed);
    }, [isZoomed, onZoomChange]);

    useEffect(() => {
        if (zoomResetRef) {
            zoomResetRef.current = resetZoom;
        }
    }, [zoomResetRef, resetZoom]);

    // Memoize the set of highlighted UIDs for O(1) checks in render functions
    const highlightedUid = highlightedSnapshot?.contentUid ?? null;
    const selected1Uid = selectedSnapshot1?.contentUid ?? null;
    const selected2Uid = selectedSnapshot2?.contentUid ?? null;

    const getPointColor = useCallback((snapshot: ContentSnapshot) => {
        const uid = snapshot.contentUid;
        if (uid === selected1Uid) return "#a855f7"; // purple-500
        if (uid === selected2Uid) return "#f97316"; // orange-500
        if (uid === highlightedUid) return "#3045ff";
        if (parentAncestors.has(uid)) return "#3045ff";
        if (coParentAncestors.has(uid)) return "#b0bae0";
        if (bestPointUids.has(uid)) return "#3fd58b";
        return "#121212"; // dark for all other points
    }, [selected1Uid, selected2Uid, highlightedUid, parentAncestors, coParentAncestors, bestPointUids]);

    // Custom shape for scatter points with dynamic radius
    const renderScatterPoint = useCallback((props: any) => {
        const { cx, cy, payload } = props;
        if (!payload?.snapshot) return <circle cx={cx} cy={cy} r={0} />;
        const uid = payload.snapshot.contentUid;
        const isActive = uid === highlightedUid || uid === selected1Uid || uid === selected2Uid;
        const radius = isActive ? 6 : 4;
        const color = getPointColor(payload.snapshot);
        const opacity = color === "#121212" ? 0.15 : 1;
        return <circle cx={cx} cy={cy} r={radius} fill={color} fillOpacity={opacity} />;
    }, [highlightedUid, selected1Uid, selected2Uid, getPointColor]);

    // Custom shape for pareto scatter points
    const renderParetoPoint = useCallback((props: any) => {
        const { cx, cy, payload } = props;
        if (!payload?.snapshot) return <circle cx={cx} cy={cy} r={0} />;
        const uid = payload.snapshot.contentUid;
        const isActive = uid === highlightedUid || uid === selected1Uid || uid === selected2Uid;
        const radius = isActive ? 6 : 4;
        let color: string;
        if (uid === selected1Uid) {
            color = "#a855f7"; // purple
        } else if (uid === selected2Uid) {
            color = "#f97316"; // orange
        } else if (uid === highlightedUid) {
            color = "#3045ff"; // blue
        } else if (payload.isPareto) {
            color = "#3fd58b"; // green
        } else {
            color = "#121212"; // dark
        }
        const opacity = color === "#121212" ? 0.15 : 1;
        return <circle cx={cx} cy={cy} r={radius} fill={color} fillOpacity={opacity} />;
    }, [highlightedUid, selected1Uid, selected2Uid]);

    // Calculate lines to draw for selected snapshots (evolution chart)
    const lineageLines = useMemo(() => {
        const getEvolutionCoords = (contentUid: string) => {
            const point = contentUidToPoint.get(contentUid);
            if (!point) return null;
            return { x: point.timestamp, y: point.fitness };
        };

        return computeLineageLines(
            [
                { snapshot: selectedSnapshot1, color: "#a855f7", coParentColor: "#c4b5fd" }, // purple / light purple
                { snapshot: selectedSnapshot2, color: "#f97316", coParentColor: "#fed7aa" }, // orange / light orange
                { snapshot: highlightedSnapshot, color: "#3045ff", coParentColor: "#b0bae0" }, // blue / light grayish
            ],
            getEvolutionCoords
        );
    }, [selectedSnapshot1, selectedSnapshot2, highlightedSnapshot, contentUidToPoint, computeLineageLines]);

    const CustomTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const point: ChartPoint = payload[0].payload;
            const isSelected1 = selectedSnapshot1?.contentUid === point.snapshot.contentUid;
            const isSelected2 = selectedSnapshot2?.contentUid === point.snapshot.contentUid;
            const fitness = point.snapshot.fitness;
            const metainfo = point.snapshot.metainfo as Record<string, unknown> | null;
            const aiSummary = metainfo?.ai_summary as { title?: string; summary?: string } | undefined;

            const renderFitness = () => {
                if (isMultiObjectiveFitness(fitness)) {
                    return (
                        <div className="text-sm space-y-0.5">
                            <span className="text-muted-foreground">Fitness:</span>
                            {Object.entries(fitness).map(([key, value]) => (
                                <div
                                    key={key}
                                    className={`ml-2 ${
                                        key === activeFitnessKey
                                            ? "font-semibold text-green-600"
                                            : "text-muted-foreground"
                                    }`}
                                >
                                    {getKeyDisplayName(key)}: {value.toFixed(4)}
                                    {key === activeFitnessKey && " ←"}
                                </div>
                            ))}
                        </div>
                    );
                }
                return (
                    <p className="text-sm">
                        <span className="text-muted-foreground">Fitness:</span>{" "}
                        <span className="font-semibold text-green-600">
                            {formatFitness(fitness)}
                        </span>
                    </p>
                );
            };

            return (
                <div className="bg-white dark:bg-slate-800 p-3 border rounded-lg shadow-lg max-w-xs">
                    {/* Primary: Title or fallback to ID */}
                    <p className="font-medium text-sm mb-2">
                        {aiSummary?.title || point.label}
                    </p>

                    {/* Metrics */}
                    {renderFitness()}
                    <p className="text-sm mt-1">
                        <span className="text-muted-foreground">Time:</span>{" "}
                        {formatTimestamp(point.timestamp)}
                    </p>

                    {/* Footer: ID + badges + action hint */}
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
                        <span className="font-mono text-xs text-muted-foreground">{point.label}</span>
                        {point.isSeed && (
                            <Badge variant="outline" className="text-xs py-0">Seed</Badge>
                        )}
                        {isSelected1 && (
                            <Badge style={{ backgroundColor: "#a855f7", color: "white" }} className="text-xs py-0">
                                1
                            </Badge>
                        )}
                        {isSelected2 && (
                            <Badge style={{ backgroundColor: "#f97316", color: "white" }} className="text-xs py-0">
                                2
                            </Badge>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                            {isComparisonMode ? "Click to compare" : "Click to view"}
                        </span>
                    </div>
                </div>
            );
        }
        return null;
    }, [selectedSnapshot1, selectedSnapshot2, activeFitnessKey, isComparisonMode]);

    // Pareto tooltip
    const ParetoTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const point = payload[0].payload;
            const fitness = point.snapshot.fitness as Record<string, number>;

            return (
                <div className="bg-white dark:bg-slate-800 p-3 border rounded-lg shadow-lg max-w-xs">
                    {/* ID as title */}
                    <p className="font-mono font-medium text-sm mb-2">{point.label}</p>

                    {/* Fitness values */}
                    <div className="text-sm space-y-0.5">
                        {Object.entries(fitness).map(([key, value]) => (
                            <div
                                key={key}
                                className={`${
                                    key === paretoXAxis || key === paretoYAxis
                                        ? "font-semibold text-green-600"
                                        : "text-muted-foreground"
                                }`}
                            >
                                {getKeyDisplayName(key)}: {value.toFixed(4)}
                            </div>
                        ))}
                    </div>

                    {/* Footer: badges + action hint */}
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
                        {point.isPareto && (
                            <Badge className="text-xs py-0 bg-amber-500">Pareto Optimal</Badge>
                        )}
                        {point.isSeed && (
                            <Badge variant="outline" className="text-xs py-0">Seed</Badge>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">Click to view</span>
                    </div>
                </div>
            );
        }
        return null;
    }, [paretoXAxis, paretoYAxis]);

    if (snapshots.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full">
                <Code className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No content snapshots available</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            <style>{`
                .evolution-chart-container *:focus,
                .evolution-chart-container *:focus-visible {
                    outline: none !important;
                    box-shadow: none !important;
                }
                .evolution-chart-container svg:focus,
                .evolution-chart-container .recharts-wrapper:focus,
                .evolution-chart-container .recharts-surface:focus {
                    outline: none !important;
                }
                .evolution-chart-container,
                .evolution-chart-container .recharts-wrapper,
                .evolution-chart-container .recharts-surface,
                .evolution-chart-container .recharts-cartesian-grid {
                    cursor: crosshair !important;
                }
                .evolution-chart-container .recharts-scatter-symbol,
                .evolution-chart-container .recharts-symbols {
                    cursor: pointer !important;
                }
            `}</style>
            {/* Chart content */}
            <div className="flex-1 min-h-0">
                {activeTab === "pareto" ? (
                    <>
                        <div
                            ref={paretoChartRef}
                            className="evolution-chart-container"
                            style={{ position: 'relative', height: '100%', minHeight: 300 }}
                            onMouseDown={handleParetoMouseDown}
                            onMouseMove={isDraggingPareto ? handleParetoMouseMove : undefined}
                            onMouseUp={handleParetoMouseUp}
                            onMouseLeave={handleParetoMouseUp}
                        >
                        {/* Y-axis label dropdown */}
                        <div
                            className="absolute z-10 flex items-center justify-center"
                            style={{
                                left: -20,
                                top: 'calc(50% - 10px)',
                                transform: 'translateY(-50%) rotate(-90deg)',
                                transformOrigin: 'center center',
                                width: 90,
                            }}
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                        >
                            {isParetoYWeighted && (
                                <button
                                    className="text-[10px] text-muted-foreground hover:text-foreground px-0.5"
                                    onClick={() => setShowParetoYWeightsPopover(!showParetoYWeightsPopover)}
                                >
                                    ⚙
                                </button>
                            )}
                            <Select
                                value={paretoYAxis ?? undefined}
                                onValueChange={(value) => {
                                    setParetoYAxis(value);
                                    if (value === "__weighted__") {
                                        setShowParetoYWeightsPopover(true);
                                    } else {
                                        setShowParetoYWeightsPopover(false);
                                    }
                                }}
                            >
                                <SelectTrigger className="h-auto py-0.5 px-1 text-[11px] text-muted-foreground border-none shadow-none bg-transparent hover:text-foreground hover:bg-muted/50 gap-0.5 font-medium">
                                    <SelectValue placeholder="Y" />
                                </SelectTrigger>
                                <SelectContent>
                                    {fitnessKeys.map((key) => (
                                        <SelectItem key={key} value={key}>
                                            {getKeyDisplayName(key)}
                                        </SelectItem>
                                    ))}
                                    <SelectItem value="__weighted__">
                                        Custom
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {/* Y-axis weights popover */}
                        {showParetoYWeightsPopover && isParetoYWeighted && (
                            <div
                                className="absolute z-20 bg-popover border rounded-lg shadow-lg p-3"
                                style={{
                                    left: 5,
                                    top: 'calc(50% - 10px)',
                                    transform: 'translateY(-50%)',
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs font-medium">Y Weights</span>
                                    <button
                                        className="text-muted-foreground hover:text-foreground text-xs ml-4"
                                        onClick={() => setShowParetoYWeightsPopover(false)}
                                    >
                                        ✕
                                    </button>
                                </div>
                                <div className="space-y-1.5">
                                    {fitnessKeys.map((key) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <label className="text-[10px] text-muted-foreground w-16 truncate">
                                                {getKeyDisplayName(key)}
                                            </label>
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.1"
                                                value={paretoYWeights[key] ?? 1}
                                                onChange={(e) =>
                                                    updateParetoYWeight(key, parseFloat(e.target.value) || 0)
                                                }
                                                className="w-14 h-6 px-1.5 text-xs border rounded bg-background"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {/* X-axis label dropdown */}
                        <div
                            className="absolute z-10 flex items-center justify-center"
                            style={{
                                left: 'calc(50% - 2px)',
                                bottom: 5,
                                transform: 'translateX(-50%)',
                                width: 90,
                            }}
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                        >
                            {isParetoXWeighted && (
                                <button
                                    className="text-[10px] text-muted-foreground hover:text-foreground px-0.5"
                                    onClick={() => setShowParetoXWeightsPopover(!showParetoXWeightsPopover)}
                                >
                                    ⚙
                                </button>
                            )}
                            <Select
                                value={paretoXAxis ?? undefined}
                                onValueChange={(value) => {
                                    setParetoXAxis(value);
                                    if (value === "__weighted__") {
                                        setShowParetoXWeightsPopover(true);
                                    } else {
                                        setShowParetoXWeightsPopover(false);
                                    }
                                }}
                            >
                                <SelectTrigger className="h-auto py-0.5 px-1 text-[11px] text-muted-foreground border-none shadow-none bg-transparent hover:text-foreground hover:bg-muted/50 gap-0.5 font-medium">
                                    <SelectValue placeholder="X" />
                                </SelectTrigger>
                                <SelectContent>
                                    {fitnessKeys.map((key) => (
                                        <SelectItem key={key} value={key}>
                                            {getKeyDisplayName(key)}
                                        </SelectItem>
                                    ))}
                                    <SelectItem value="__weighted__">
                                        Custom
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {/* X-axis weights popover */}
                        {showParetoXWeightsPopover && isParetoXWeighted && (
                            <div
                                className="absolute z-20 bg-popover border rounded-lg shadow-lg p-3"
                                style={{
                                    left: 'calc(50% - 2px)',
                                    bottom: 45,
                                    transform: 'translateX(-50%)',
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs font-medium">X Weights</span>
                                    <button
                                        className="text-muted-foreground hover:text-foreground text-xs ml-4"
                                        onClick={() => setShowParetoXWeightsPopover(false)}
                                    >
                                        ✕
                                    </button>
                                </div>
                                <div className="space-y-1.5">
                                    {fitnessKeys.map((key) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <label className="text-[10px] text-muted-foreground w-16 truncate">
                                                {getKeyDisplayName(key)}
                                            </label>
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.1"
                                                value={paretoXWeights[key] ?? 1}
                                                onChange={(e) =>
                                                    updateParetoXWeight(key, parseFloat(e.target.value) || 0)
                                                }
                                                className="w-14 h-6 px-1.5 text-xs border rounded bg-background"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart
                                margin={chartMargin}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                    type="number"
                                    dataKey="x"
                                    name={isParetoXWeighted ? "Custom" : (paretoXAxis ? getKeyDisplayName(paretoXAxis) : "X")}
                                    domain={paretoZoom ? paretoZoom.x : [paretoBounds.xMin, paretoBounds.xMax]}
                                    allowDataOverflow
                                    ticks={paretoTicks.xTicks}
                                    tick={{ fontSize: 11 }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="y"
                                    name={isParetoYWeighted ? "Custom" : (paretoYAxis ? getKeyDisplayName(paretoYAxis) : "Y")}
                                    domain={paretoZoom ? paretoZoom.y : [paretoBounds.yMin, paretoBounds.yMax]}
                                    allowDataOverflow
                                    ticks={paretoTicks.yTicks}
                                    tick={{ fontSize: 11 }}
                                />
                                <Tooltip content={<ParetoTooltip />} wrapperStyle={{ pointerEvents: 'none' }} />

                                {/* Pareto frontier line - rendered with pointer-events:none to not interfere with scatter hover */}
                                {paretoData.frontierLine.length > 1 && (
                                    <Line
                                        data={paretoData.frontierLine}
                                        dataKey="y"
                                        stroke="#3fd58b"
                                        strokeWidth={2}
                                        strokeDasharray="5 5"
                                        dot={false}
                                        isAnimationActive={false}
                                        style={{ pointerEvents: 'none' }}
                                        activeDot={false}
                                    />
                                )}

                                {/* All points */}
                                <Scatter
                                    data={filteredParetoData.allPoints}
                                    fill="#121212"
                                    cursor="pointer"
                                    isAnimationActive={false}
                                    shape={renderParetoPoint}
                                    onClick={(data: any) => {
                                        if (data && data.snapshot) {
                                            if (isComparisonMode && onSelectForComparison) {
                                                onSelectForComparison(data.snapshot);
                                            } else if (onPointClick) {
                                                onPointClick(data.snapshot);
                                            }
                                        }
                                    }}
                                />
                            </ScatterChart>
                        </ResponsiveContainer>
                        {/* Selection box overlay (pixel-based) */}
                        {paretoSelectionPx && (
                            <div
                                style={{
                                    position: 'absolute',
                                    left: Math.min(paretoSelectionPx.x1, paretoSelectionPx.x2),
                                    top: Math.min(paretoSelectionPx.y1, paretoSelectionPx.y2),
                                    width: Math.abs(paretoSelectionPx.x2 - paretoSelectionPx.x1),
                                    height: Math.abs(paretoSelectionPx.y2 - paretoSelectionPx.y1),
                                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                                    border: '1px solid rgba(59, 130, 246, 0.6)',
                                    pointerEvents: 'none',
                                }}
                            />
                        )}
                        </div>
                    </>
                ) : (
                    <>
                        <div
                            ref={evolutionChartRef}
                            className="evolution-chart-container"
                            style={{ position: 'relative', height: '100%', minHeight: 300 }}
                            onMouseDown={handleEvolutionMouseDown}
                            onMouseMove={isDraggingEvolution ? handleEvolutionMouseMove : undefined}
                            onMouseUp={handleEvolutionMouseUp}
                            onMouseLeave={handleEvolutionMouseUp}
                        >
                        {/* Y-axis label as clickable dropdown */}
                        {isMultiObjective ? (
                            <div
                                className="absolute z-10 flex items-center justify-center"
                                style={{
                                    left: -20,
                                    top: 'calc(50% - 10px)',
                                    transform: 'translateY(-50%) rotate(-90deg)',
                                    transformOrigin: 'center center',
                                    width: 90,
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                            >
                                {isWeightedMode && (
                                    <button
                                        className="text-[10px] text-muted-foreground hover:text-foreground px-0.5"
                                        onClick={() => setShowWeightsPopover(!showWeightsPopover)}
                                    >
                                        ⚙
                                    </button>
                                )}
                                <Select
                                    value={isWeightedMode ? "__weighted__" : (activeFitnessKey ?? undefined)}
                                    onValueChange={(value) => {
                                        setSelectedFitnessKey(value);
                                        if (value === "__weighted__") {
                                            setShowWeightsPopover(true);
                                        } else {
                                            setShowWeightsPopover(false);
                                        }
                                    }}
                                >
                                    <SelectTrigger className="h-auto py-0.5 px-1 text-[11px] text-muted-foreground border-none shadow-none bg-transparent hover:text-foreground hover:bg-muted/50 gap-0.5 font-medium">
                                        <SelectValue placeholder="Fitness" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {fitnessKeys.map((key) => (
                                            <SelectItem key={key} value={key}>
                                                {getKeyDisplayName(key)}
                                            </SelectItem>
                                        ))}
                                        <SelectItem value="__weighted__">
                                            Custom
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        ) : (
                            <div
                                className="absolute z-10 text-[11px] text-muted-foreground font-medium"
                                style={{
                                    left: -20,
                                    top: 'calc(50% - 10px)',
                                    transform: 'translateY(-50%) rotate(-90deg)',
                                    transformOrigin: 'center center',
                                    width: 80,
                                    textAlign: 'center',
                                }}
                            >
                                Fitness
                            </div>
                        )}
                        {/* Weights popover for Custom mode */}
                        {showWeightsPopover && isWeightedMode && (
                            <div
                                className="absolute z-20 bg-popover border rounded-lg shadow-lg p-3"
                                style={{
                                    left: 5,
                                    top: 'calc(50% - 10px)',
                                    transform: 'translateY(-50%)',
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs font-medium">Weights</span>
                                    <button
                                        className="text-muted-foreground hover:text-foreground text-xs ml-4"
                                        onClick={() => setShowWeightsPopover(false)}
                                    >
                                        ✕
                                    </button>
                                </div>
                                <div className="space-y-1.5">
                                    {fitnessKeys.map((key) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <label className="text-[10px] text-muted-foreground w-16 truncate">
                                                {getKeyDisplayName(key)}
                                            </label>
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.1"
                                                value={weights[key] ?? 1}
                                                onChange={(e) =>
                                                    updateWeight(key, parseFloat(e.target.value) || 0)
                                                }
                                                className="w-14 h-6 px-1.5 text-xs border rounded bg-background"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart
                                margin={chartMargin}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                    type="number"
                                    dataKey="timestamp"
                                    name="Elapsed Time"
                                    domain={evolutionZoom ? evolutionZoom.x : [evolutionBounds.xMin, evolutionBounds.xMax]}
                                    allowDataOverflow
                                    ticks={evolutionTicks.xTicks}
                                    tickFormatter={formatTimestamp}
                                    tick={{ fontSize: 11 }}
                                    label={{
                                        value: "Elapsed Time",
                                        position: "bottom",
                                        offset: 0,
                                        style: { fontSize: 11, textAnchor: 'middle', fill: 'hsl(var(--muted-foreground))' }
                                    }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="fitness"
                                    name="Fitness"
                                    domain={evolutionZoom ? evolutionZoom.y : [evolutionBounds.yMin, evolutionBounds.yMax]}
                                    allowDataOverflow
                                    ticks={evolutionTicks.yTicks}
                                    tick={{ fontSize: 11 }}
                                />
                                <Tooltip content={<CustomTooltip />} wrapperStyle={{ pointerEvents: 'none' }} />

                        {/* Best over time frontier line (green, step-like) */}
                        {bestOverTimeLine.length > 1 && (
                            <Line
                                data={bestOverTimeLine}
                                dataKey="fitness"
                                stroke="#3fd58b"
                                strokeWidth={2}
                                strokeDasharray="5 5"
                                dot={false}
                                isAnimationActive={false}
                                style={{ pointerEvents: 'none' }}
                                activeDot={false}
                                type="stepAfter"
                            />
                        )}

                        {/* Lineage lines: co-parent (behind, dotted) */}
                        {lineageLines.coParentLines.map((line, index) => (
                            <Line
                                key={`coparent-line-${index}`}
                                data={[
                                    { timestamp: line.x1, fitness: line.y1 },
                                    { timestamp: line.x2, fitness: line.y2 },
                                ]}
                                dataKey="fitness"
                                stroke={line.color}
                                strokeWidth={2}
                                strokeOpacity={0.4}
                                strokeDasharray="4 4"
                                dot={false}
                                isAnimationActive={false}
                                style={{ pointerEvents: 'none' }}
                                activeDot={false}
                            />
                        ))}

                        {/* Lineage lines: parent (on top, solid) */}
                        {lineageLines.parentLines.map((line, index) => (
                            <Line
                                key={`lineage-line-${index}`}
                                data={[
                                    { timestamp: line.x1, fitness: line.y1 },
                                    { timestamp: line.x2, fitness: line.y2 },
                                ]}
                                dataKey="fitness"
                                stroke={line.color}
                                strokeWidth={3}
                                strokeOpacity={0.8}
                                dot={false}
                                isAnimationActive={false}
                                style={{ pointerEvents: 'none' }}
                                activeDot={false}
                            />
                        ))}

                        {/* Regular points (rendered first, below) */}
                        <Scatter
                            data={regularPoints}
                            fill="#121212"
                            cursor="pointer"
                            isAnimationActive={false}
                            shape={renderScatterPoint}
                            onClick={(data: ChartPoint) => {
                                if (data && data.snapshot) {
                                    if (isComparisonMode && onSelectForComparison) {
                                        onSelectForComparison(data.snapshot);
                                    } else if (onPointClick) {
                                        onPointClick(data.snapshot);
                                    }
                                }
                            }}
                        />

                        {/* Best Over Time points (rendered last, on top) */}
                        <Scatter
                            data={bestPoints}
                            fill="#3fd58b"
                            cursor="pointer"
                            isAnimationActive={false}
                            shape={renderScatterPoint}
                            onClick={(data: ChartPoint) => {
                                if (data && data.snapshot) {
                                    if (isComparisonMode && onSelectForComparison) {
                                        onSelectForComparison(data.snapshot);
                                    } else if (onPointClick) {
                                        onPointClick(data.snapshot);
                                    }
                                }
                            }}
                        />
                    </ScatterChart>
                </ResponsiveContainer>
                {/* Selection box overlay (pixel-based) */}
                {evolutionSelectionPx && (
                    <div
                        style={{
                            position: 'absolute',
                            left: Math.min(evolutionSelectionPx.x1, evolutionSelectionPx.x2),
                            top: Math.min(evolutionSelectionPx.y1, evolutionSelectionPx.y2),
                            width: Math.abs(evolutionSelectionPx.x2 - evolutionSelectionPx.x1),
                            height: Math.abs(evolutionSelectionPx.y2 - evolutionSelectionPx.y1),
                            backgroundColor: 'rgba(59, 130, 246, 0.2)',
                            border: '1px solid rgba(59, 130, 246, 0.6)',
                            pointerEvents: 'none',
                        }}
                    />
                )}
                </div>
                    </>
                    )}
            </div>
        </div>
    );
}

const ContentEvolutionChart = memo(ContentEvolutionChartInner);
export default ContentEvolutionChart;
