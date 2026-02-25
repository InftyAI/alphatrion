import { memo, useState } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { Activity } from "lucide-react";
import { Badge } from "../ui/badge";
import type { Metric } from "../../types";

const COLORS = [
    "#3b82f6", // blue
    "#10b981", // green
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // purple
    "#ec4899", // pink
    "#14b8a6", // teal
    "#f97316", // orange
];

interface TrialMetricsInlineProps {
    metrics: Metric[];
    isLoading: boolean;
}

export const TrialMetricsInline = memo(function TrialMetricsInline({
    metrics,
    isLoading,
}: TrialMetricsInlineProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
            </div>
        );
    }

    if (metrics.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                <Activity className="h-8 w-8" />
                <p className="text-sm">No metrics recorded</p>
            </div>
        );
    }

    // Group metrics by key
    const metricsByKey: Record<string, Metric[]> = {};
    for (const m of metrics) {
        const key = m.key || "unknown";
        if (!metricsByKey[key]) metricsByKey[key] = [];
        metricsByKey[key].push(m);
    }
    const metricKeys = Object.keys(metricsByKey);

    return <MetricsChart metricsByKey={metricsByKey} metricKeys={metricKeys} />;
});

// Separate inner component so useState is not conditional
const MetricsChart = memo(function MetricsChart({
    metricsByKey,
    metricKeys,
}: {
    metricsByKey: Record<string, Metric[]>;
    metricKeys: string[];
}) {
    const [visibleMetrics, setVisibleMetrics] = useState<Set<string>>(
        () => new Set(metricKeys),
    );

    const toggleMetric = (key: string) => {
        setVisibleMetrics((prev) => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    // Build chart data: one row per step index
    const maxLength = Math.max(
        ...metricKeys.map((k) => metricsByKey[k].length),
    );
    const chartData = Array.from({ length: maxLength }, (_, index) => {
        const point: Record<string, number> = { index: index + 1 };
        for (const key of metricKeys) {
            const list = metricsByKey[key];
            if (index < list.length) {
                point[key] = list[index].value ?? 0;
            }
        }
        return point;
    });

    return (
        <div className="flex flex-col h-full gap-1">
            {/* Metric key badges */}
            <div className="flex flex-wrap gap-1 px-1 flex-shrink-0">
                {metricKeys.map((key, idx) => (
                    <Badge
                        key={key}
                        variant={visibleMetrics.has(key) ? "default" : "outline"}
                        className="cursor-pointer text-[10px] px-1.5 py-0"
                        style={{
                            backgroundColor: visibleMetrics.has(key)
                                ? COLORS[idx % COLORS.length]
                                : undefined,
                            borderColor: COLORS[idx % COLORS.length],
                        }}
                        onClick={() => toggleMetric(key)}
                    >
                        {key}
                    </Badge>
                ))}
            </div>
            {/* Chart */}
            <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={chartData}
                        margin={{ top: 4, right: 12, left: 0, bottom: 4 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                            dataKey="index"
                            tick={{ fontSize: 10 }}
                            stroke="#6b7280"
                        />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6b7280" />
                        <Tooltip
                            contentStyle={{
                                fontSize: "11px",
                                borderRadius: "6px",
                                padding: "6px 10px",
                            }}
                        />
                        {metricKeys.map((key, idx) => {
                            if (!visibleMetrics.has(key)) return null;
                            return (
                                <Line
                                    key={key}
                                    type="monotone"
                                    dataKey={key}
                                    stroke={COLORS[idx % COLORS.length]}
                                    strokeWidth={1.5}
                                    dot={false}
                                    activeDot={{ r: 3 }}
                                />
                            );
                        })}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
});
