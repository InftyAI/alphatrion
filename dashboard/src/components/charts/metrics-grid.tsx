import { useMemo } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Brush,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import type { Metric } from "../../types";

interface MetricsGridProps {
    metrics: Metric[];
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
    const metricsByKey = useMemo(() => {
        const grouped: Record<string, Metric[]> = {};
        metrics.forEach((m) => {
            const key = m.key || "unknown";
            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(m);
        });
        return grouped;
    }, [metrics]);

    const metricKeys = Object.keys(metricsByKey);

    if (metrics.length === 0) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <Activity className="w-12 h-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">No metrics data available</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {metricKeys.map((key) => {
                const metricData = metricsByKey[key];
                const chartData = metricData.map((m, idx) => ({
                    index: idx + 1,
                    value: m.value ?? 0,
                    step: m.step ?? idx + 1,
                }));

                const values = metricData.map((m) => m.value ?? 0);
                const min = Math.min(...values);
                const max = Math.max(...values);
                const avg = values.reduce((a, b) => a + b, 0) / values.length;
                const latest = values[values.length - 1] ?? 0;

                // Calculate trend
                let trend: "up" | "down" | "flat" = "flat";
                if (values.length >= 2) {
                    const first = values[0];
                    const last = values[values.length - 1];
                    const change = ((last - first) / (first || 1)) * 100;
                    if (change > 1) trend = "up";
                    else if (change < -1) trend = "down";
                }

                const TrendIcon =
                    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Activity;
                const trendColor =
                    trend === "up"
                        ? "text-green-500"
                        : trend === "down"
                        ? "text-red-500"
                        : "text-gray-500";

                return (
                    <Card key={key}>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg">{key}</CardTitle>
                                <TrendIcon className={`h-5 w-5 ${trendColor}`} />
                            </div>
                            <div className="flex items-center gap-2 mt-2">
                                <Badge variant="secondary">
                                    Latest: {latest.toFixed(4)}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                    {metricData.length} points
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis
                                        dataKey="step"
                                        label={{
                                            value: "Step",
                                            position: "insideBottom",
                                            offset: -5,
                                        }}
                                        stroke="#6b7280"
                                        tick={{ fontSize: 12 }}
                                    />
                                    <YAxis
                                        stroke="#6b7280"
                                        tick={{ fontSize: 12 }}
                                        domain={["auto", "auto"]}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "white",
                                            border: "1px solid #e5e7eb",
                                            borderRadius: "8px",
                                            padding: "8px",
                                        }}
                                        labelFormatter={(value) => `Step: ${value}`}
                                        formatter={(value: any) => [
                                            value.toFixed(4),
                                            key,
                                        ]}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4 }}
                                    />
                                    {metricData.length > 20 && (
                                        <Brush
                                            dataKey="step"
                                            height={20}
                                            stroke="#3b82f6"
                                            fill="#eff6ff"
                                        />
                                    )}
                                </LineChart>
                            </ResponsiveContainer>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t">
                                <div className="text-center">
                                    <p className="text-xs text-muted-foreground">Min</p>
                                    <p className="text-sm font-medium">{min.toFixed(4)}</p>
                                </div>
                                <div className="text-center">
                                    <p className="text-xs text-muted-foreground">Avg</p>
                                    <p className="text-sm font-medium">{avg.toFixed(4)}</p>
                                </div>
                                <div className="text-center">
                                    <p className="text-xs text-muted-foreground">Max</p>
                                    <p className="text-sm font-medium">{max.toFixed(4)}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}
