import { useState, useMemo } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Brush,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Download, TrendingUp } from "lucide-react";
import type { Metric } from "../../types";

interface MultiTrialComparisonProps {
    metrics: (Metric & { trialId: string })[];
    trialNames: Record<string, string>; // trialId -> trial name
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

export default function MultiTrialComparison({ metrics, trialNames }: MultiTrialComparisonProps) {
    // Get available metric keys
    const metricKeys = useMemo(() => {
        const keys = new Set<string>();
        metrics.forEach((m) => {
            if (m.key) keys.add(m.key);
        });
        return Array.from(keys).sort();
    }, [metrics]);

    const [selectedMetric, setSelectedMetric] = useState<string>(metricKeys[0] || "");

    // Get unique trial IDs
    const trialIds = useMemo(() => {
        const ids = new Set<string>();
        metrics.forEach((m) => ids.add(m.trialId));
        return Array.from(ids);
    }, [metrics]);

    // Prepare chart data
    const chartData = useMemo(() => {
        if (!selectedMetric) return [];

        // Group metrics by trial
        const trialMetrics: Record<string, Metric[]> = {};
        metrics.forEach((m) => {
            if (m.key === selectedMetric) {
                if (!trialMetrics[m.trialId]) trialMetrics[m.trialId] = [];
                trialMetrics[m.trialId].push(m);
            }
        });

        // Find max length
        const maxLength = Math.max(...Object.values(trialMetrics).map((arr) => arr.length), 0);

        // Create aligned data
        const data = Array.from({ length: maxLength }, (_, idx) => {
            const point: any = { step: idx + 1 };
            Object.entries(trialMetrics).forEach(([trialId, metrics]) => {
                if (idx < metrics.length) {
                    point[trialId] = metrics[idx].value;
                }
            });
            return point;
        });

        return data;
    }, [metrics, selectedMetric]);

    // Calculate statistics
    const stats = useMemo(() => {
        if (!selectedMetric) return null;

        const trialStats: Record<string, { min: number; max: number; avg: number; latest: number }> = {};

        trialIds.forEach((trialId) => {
            const trialMetrics = metrics.filter((m) => m.trialId === trialId && m.key === selectedMetric);
            if (trialMetrics.length === 0) return;

            const values = trialMetrics.map((m) => m.value ?? 0);
            trialStats[trialId] = {
                min: Math.min(...values),
                max: Math.max(...values),
                avg: values.reduce((a, b) => a + b, 0) / values.length,
                latest: values[values.length - 1] ?? 0,
            };
        });

        return trialStats;
    }, [metrics, selectedMetric, trialIds]);

    const exportData = () => {
        if (!selectedMetric) return;

        const csv = [
            ["Step", ...trialIds.map((id) => trialNames[id] || id)].join(","),
            ...chartData.map((row) => [row.step, ...trialIds.map((id) => row[id] ?? "")].join(",")),
        ].join("\n");

        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `multi_trial_${selectedMetric}.csv`;
        a.click();
    };

    if (metricKeys.length === 0) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <p className="text-muted-foreground">No metrics available</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle>Multi-Trial Comparison</CardTitle>
                    <CardDescription>Compare the same metric across {trialIds.length} trials</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-4">
                        <div className="flex-1 max-w-xs">
                            <label className="text-sm font-medium mb-2 block">Select Metric</label>
                            <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Choose a metric" />
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
                            <Button variant="outline" onClick={exportData} disabled={!selectedMetric}>
                                <Download className="w-4 h-4 mr-2" />
                                Export CSV
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Trial Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {trialIds.map((trialId, idx) => {
                        const stat = stats[trialId];
                        if (!stat) return null;

                        return (
                            <Card key={trialId}>
                                <CardHeader className="pb-3">
                                    <div className="flex items-center gap-2">
                                        <div
                                            className="w-3 h-3 rounded-full"
                                            style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                                        />
                                        <CardTitle className="text-sm font-medium truncate">
                                            {trialNames[trialId] || trialId}
                                        </CardTitle>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold mb-2">{stat.latest.toFixed(4)}</div>
                                    <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                                        <div>
                                            <p>Min</p>
                                            <p className="font-medium text-foreground">{stat.min.toFixed(3)}</p>
                                        </div>
                                        <div>
                                            <p>Avg</p>
                                            <p className="font-medium text-foreground">{stat.avg.toFixed(3)}</p>
                                        </div>
                                        <div>
                                            <p>Max</p>
                                            <p className="font-medium text-foreground">{stat.max.toFixed(3)}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>{selectedMetric || "Select a metric"} - All Trials</CardTitle>
                    <CardDescription>
                        Comparison of {selectedMetric} across {trialIds.length} trials
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {chartData.length === 0 ? (
                        <div className="flex items-center justify-center h-96 text-muted-foreground">
                            No data available for selected metric
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis
                                    dataKey="step"
                                    label={{ value: "Step", position: "insideBottom", offset: -5 }}
                                    stroke="#6b7280"
                                />
                                <YAxis stroke="#6b7280" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: "white",
                                        border: "1px solid #e5e7eb",
                                        borderRadius: "8px",
                                        padding: "12px",
                                    }}
                                    labelFormatter={(value) => `Step: ${value}`}
                                    formatter={(value: any, name: string) => [
                                        value.toFixed(4),
                                        trialNames[name] || name,
                                    ]}
                                />
                                <Legend
                                    formatter={(value) => trialNames[value] || value}
                                    wrapperStyle={{ paddingTop: "20px" }}
                                />
                                <Brush dataKey="step" height={30} stroke="#3b82f6" fill="#eff6ff" />

                                {trialIds.map((trialId, idx) => (
                                    <Line
                                        key={trialId}
                                        type="monotone"
                                        dataKey={trialId}
                                        stroke={COLORS[idx % COLORS.length]}
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4 }}
                                        name={trialNames[trialId] || trialId}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
