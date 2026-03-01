import { useState, useMemo } from "react";
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ZAxis,
    Legend,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { ArrowRight, Download } from "lucide-react";
import type { Metric } from "../../types";

interface MetricsComparisonProps {
    metrics: Metric[];
}

export default function MetricsComparison({ metrics }: MetricsComparisonProps) {
    const metricKeys = useMemo(() => {
        const keys = new Set<string>();
        metrics.forEach((m) => {
            if (m.key) keys.add(m.key);
        });
        return Array.from(keys).sort();
    }, [metrics]);

    const [xAxis, setXAxis] = useState<string>(metricKeys[0] || "");
    const [yAxis, setYAxis] = useState<string>(metricKeys[1] || metricKeys[0] || "");

    const chartData = useMemo(() => {
        if (!xAxis || !yAxis) return [];

        // Group metrics by run_id to get paired values
        const runData: Record<string, { x?: number; y?: number; step?: number }> = {};

        metrics.forEach((m) => {
            const runKey = m.runId || "default";
            if (!runData[runKey]) runData[runKey] = {};

            if (m.key === xAxis) {
                runData[runKey].x = m.value ?? 0;
                runData[runKey].step = m.step ?? 0;
            }
            if (m.key === yAxis) {
                runData[runKey].y = m.value ?? 0;
            }
        });

        // Filter to only runs with both x and y values
        return Object.entries(runData)
            .filter(([_, data]) => data.x !== undefined && data.y !== undefined)
            .map(([runId, data], idx) => ({
                x: data.x!,
                y: data.y!,
                step: data.step,
                runId,
                index: idx + 1,
            }));
    }, [metrics, xAxis, yAxis]);

    const stats = useMemo(() => {
        if (chartData.length === 0) return null;

        const xValues = chartData.map((d) => d.x);
        const yValues = chartData.map((d) => d.y);

        // Calculate correlation coefficient
        const n = xValues.length;
        const sumX = xValues.reduce((a, b) => a + b, 0);
        const sumY = yValues.reduce((a, b) => a + b, 0);
        const sumXY = xValues.reduce((sum, x, i) => sum + x * yValues[i], 0);
        const sumX2 = xValues.reduce((sum, x) => sum + x * x, 0);
        const sumY2 = yValues.reduce((sum, y) => sum + y * y, 0);

        const correlation =
            (n * sumXY - sumX * sumY) /
            Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

        return {
            correlation: isNaN(correlation) ? 0 : correlation,
            xMin: Math.min(...xValues),
            xMax: Math.max(...xValues),
            yMin: Math.min(...yValues),
            yMax: Math.max(...yValues),
            points: chartData.length,
        };
    }, [chartData]);

    const exportData = () => {
        const csv = [
            ["Index", xAxis, yAxis, "Step", "Run ID"].join(","),
            ...chartData.map((row) =>
                [row.index, row.x, row.y, row.step, row.runId].join(",")
            ),
        ].join("\n");

        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `comparison_${xAxis}_vs_${yAxis}.csv`;
        a.click();
    };

    if (metricKeys.length === 0) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <p className="text-muted-foreground">No metrics available for comparison</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle>Metric Comparison</CardTitle>
                    <CardDescription>
                        Select two metrics to visualize their relationship
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-4 flex-wrap">
                        <div className="flex-1 min-w-[200px]">
                            <label className="text-sm font-medium mb-2 block">
                                X-Axis (Horizontal)
                            </label>
                            <Select value={xAxis} onValueChange={setXAxis}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select metric" />
                                </SelectTrigger>
                                <SelectContent>
                                    {metricKeys.map((key) => (
                                        <SelectItem key={key} value={key}>
                                            {key}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-center justify-center pt-6">
                            <ArrowRight className="w-5 h-5 text-muted-foreground" />
                        </div>

                        <div className="flex-1 min-w-[200px]">
                            <label className="text-sm font-medium mb-2 block">
                                Y-Axis (Vertical)
                            </label>
                            <Select value={yAxis} onValueChange={setYAxis}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select metric" />
                                </SelectTrigger>
                                <SelectContent>
                                    {metricKeys.map((key) => (
                                        <SelectItem key={key} value={key}>
                                            {key}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="pt-6">
                            <Button
                                variant="outline"
                                onClick={exportData}
                                disabled={chartData.length === 0}
                            >
                                <Download className="w-4 h-4 mr-2" />
                                Export
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Stats */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium">
                                Correlation
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {stats.correlation.toFixed(3)}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                                {Math.abs(stats.correlation) > 0.7
                                    ? "Strong"
                                    : Math.abs(stats.correlation) > 0.4
                                    ? "Moderate"
                                    : "Weak"}{" "}
                                {stats.correlation > 0 ? "positive" : "negative"}
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium">
                                {xAxis} Range
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-lg font-bold">
                                {stats.xMin.toFixed(3)} - {stats.xMax.toFixed(3)}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                                Span: {(stats.xMax - stats.xMin).toFixed(3)}
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium">
                                {yAxis} Range
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-lg font-bold">
                                {stats.yMin.toFixed(3)} - {stats.yMax.toFixed(3)}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                                Span: {(stats.yMax - stats.yMin).toFixed(3)}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Scatter Plot */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>
                                {yAxis} vs {xAxis}
                            </CardTitle>
                            <CardDescription>
                                {chartData.length} data points
                            </CardDescription>
                        </div>
                        {stats && (
                            <Badge
                                variant={
                                    Math.abs(stats.correlation) > 0.7
                                        ? "default"
                                        : Math.abs(stats.correlation) > 0.4
                                        ? "secondary"
                                        : "outline"
                                }
                            >
                                r = {stats.correlation.toFixed(3)}
                            </Badge>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    {chartData.length === 0 ? (
                        <div className="flex items-center justify-center h-96 text-muted-foreground">
                            No data points available for selected metrics
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={400}>
                            <ScatterChart
                                margin={{ top: 20, right: 20, bottom: 60, left: 60 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis
                                    type="number"
                                    dataKey="x"
                                    name={xAxis}
                                    label={{
                                        value: xAxis,
                                        position: "insideBottom",
                                        offset: -10,
                                        style: { fontSize: 14, fontWeight: 600 },
                                    }}
                                    stroke="#6b7280"
                                />
                                <YAxis
                                    type="number"
                                    dataKey="y"
                                    name={yAxis}
                                    label={{
                                        value: yAxis,
                                        angle: -90,
                                        position: "insideLeft",
                                        style: { fontSize: 14, fontWeight: 600 },
                                    }}
                                    stroke="#6b7280"
                                />
                                <ZAxis type="number" dataKey="index" range={[50, 400]} />
                                <Tooltip
                                    cursor={{ strokeDasharray: "3 3" }}
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            const data = payload[0].payload;
                                            return (
                                                <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
                                                    <p className="font-semibold mb-2">
                                                        Point {data.index}
                                                    </p>
                                                    <div className="space-y-1 text-sm">
                                                        <p>
                                                            <span className="text-muted-foreground">
                                                                {xAxis}:
                                                            </span>{" "}
                                                            {data.x.toFixed(4)}
                                                        </p>
                                                        <p>
                                                            <span className="text-muted-foreground">
                                                                {yAxis}:
                                                            </span>{" "}
                                                            {data.y.toFixed(4)}
                                                        </p>
                                                        {data.step !== undefined && (
                                                            <p>
                                                                <span className="text-muted-foreground">
                                                                    Step:
                                                                </span>{" "}
                                                                {data.step}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                <Scatter
                                    name={`${yAxis} vs ${xAxis}`}
                                    data={chartData}
                                    fill="#3b82f6"
                                    fillOpacity={0.6}
                                />
                            </ScatterChart>
                        </ResponsiveContainer>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
