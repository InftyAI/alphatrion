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
    Area,
    ComposedChart,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs-new";
import {
    TrendingUp,
    TrendingDown,
    Activity,
    BarChart3,
    LineChartIcon,
    Download,
} from "lucide-react";
import type { Metric } from "../../types";

interface InteractiveMetricsChartProps {
    metrics: Metric[];
}

// Color palette for different metrics
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

export default function InteractiveMetricsChart({ metrics }: InteractiveMetricsChartProps) {
    const [chartType, setChartType] = useState<"line" | "area">("line");
    const [visibleMetrics, setVisibleMetrics] = useState<Set<string>>(new Set());

    // Group metrics by key and organize data
    const { metricKeys, chartData, stats } = useMemo(() => {
        const metricsByKey: Record<string, Metric[]> = {};
        metrics.forEach((m) => {
            const key = m.key || "unknown";
            if (!metricsByKey[key]) metricsByKey[key] = [];
            metricsByKey[key].push(m);
        });

        const keys = Object.keys(metricsByKey);

        // Initialize visible metrics (all visible by default)
        if (visibleMetrics.size === 0 && keys.length > 0) {
            setVisibleMetrics(new Set(keys));
        }

        // Create chart data - combine all metrics by index
        const maxLength = Math.max(...keys.map((k) => metricsByKey[k].length));
        const data = Array.from({ length: maxLength }, (_, index) => {
            const point: any = { index: index + 1 };
            keys.forEach((key) => {
                const metricList = metricsByKey[key];
                if (index < metricList.length) {
                    point[key] = metricList[index].value;
                    // Add timestamp if available
                    if (metricList[index].createdAt) {
                        point[`${key}_timestamp`] = metricList[index].createdAt;
                    }
                }
            });
            return point;
        });

        // Calculate statistics for each metric
        const statistics: Record<
            string,
            { min: number; max: number; avg: number; latest: number; trend: "up" | "down" | "flat" }
        > = {};

        keys.forEach((key) => {
            const values = metricsByKey[key].map((m) => m.value ?? 0);
            const min = Math.min(...values);
            const max = Math.max(...values);
            const avg = values.reduce((a, b) => a + b, 0) / values.length;
            const latest = values[values.length - 1] ?? 0;

            // Determine trend
            let trend: "up" | "down" | "flat" = "flat";
            if (values.length >= 2) {
                const first = values[0];
                const last = values[values.length - 1];
                const change = ((last - first) / (first || 1)) * 100;
                if (change > 1) trend = "up";
                else if (change < -1) trend = "down";
            }

            statistics[key] = { min, max, avg, latest, trend };
        });

        return {
            metricKeys: keys,
            chartData: data,
            stats: statistics,
        };
    }, [metrics]);

    const toggleMetric = (key: string) => {
        const newVisible = new Set(visibleMetrics);
        if (newVisible.has(key)) {
            newVisible.delete(key);
        } else {
            newVisible.add(key);
        }
        setVisibleMetrics(newVisible);
    };

    const exportData = () => {
        const csv = [
            ["Index", ...metricKeys].join(","),
            ...chartData.map((row) =>
                [row.index, ...metricKeys.map((key) => row[key] ?? "")].join(",")
            ),
        ].join("\n");

        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "metrics.csv";
        a.click();
    };

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
        <div className="space-y-6">
            {/* Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {metricKeys.slice(0, 4).map((key, idx) => {
                    const stat = stats[key];
                    const TrendIcon = stat.trend === "up" ? TrendingUp : stat.trend === "down" ? TrendingDown : Activity;
                    const trendColor = stat.trend === "up" ? "text-green-500" : stat.trend === "down" ? "text-red-500" : "text-gray-500";

                    return (
                        <Card key={key}>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium truncate">{key}</CardTitle>
                                <TrendIcon className={`h-4 w-4 ${trendColor}`} />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{stat.latest.toFixed(4)}</div>
                                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                    <span>Min: {stat.min.toFixed(2)}</span>
                                    <span>Max: {stat.max.toFixed(2)}</span>
                                    <span>Avg: {stat.avg.toFixed(2)}</span>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Chart Controls */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Metrics Over Time</CardTitle>
                            <CardDescription>
                                Interactive visualization of {metricKeys.length} metric(s) across {chartData.length} steps
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Tabs value={chartType} onValueChange={(v) => setChartType(v as any)}>
                                <TabsList>
                                    <TabsTrigger value="line">
                                        <LineChartIcon className="w-4 h-4 mr-1" />
                                        Line
                                    </TabsTrigger>
                                    <TabsTrigger value="area">
                                        <BarChart3 className="w-4 h-4 mr-1" />
                                        Area
                                    </TabsTrigger>
                                </TabsList>
                            </Tabs>
                            <Button variant="outline" size="sm" onClick={exportData}>
                                <Download className="w-4 h-4 mr-1" />
                                Export CSV
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Metric Toggle Badges */}
                    <div className="flex flex-wrap gap-2 mb-4">
                        {metricKeys.map((key, idx) => (
                            <Badge
                                key={key}
                                variant={visibleMetrics.has(key) ? "default" : "outline"}
                                className="cursor-pointer hover:scale-105 transition-transform"
                                style={{
                                    backgroundColor: visibleMetrics.has(key) ? COLORS[idx % COLORS.length] : undefined,
                                    borderColor: COLORS[idx % COLORS.length],
                                }}
                                onClick={() => toggleMetric(key)}
                            >
                                <span
                                    className="w-2 h-2 rounded-full mr-1.5"
                                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                                />
                                {key}
                            </Badge>
                        ))}
                    </div>

                    {/* Chart */}
                    <ResponsiveContainer width="100%" height={400}>
                        <ComposedChart
                            data={chartData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                                dataKey="index"
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
                                labelStyle={{ fontWeight: "bold", marginBottom: "8px" }}
                            />
                            <Legend
                                wrapperStyle={{ paddingTop: "20px" }}
                                onClick={(e) => toggleMetric(e.dataKey as string)}
                            />
                            <Brush
                                dataKey="index"
                                height={30}
                                stroke="#3b82f6"
                                fill="#eff6ff"
                            />

                            {metricKeys.map((key, idx) => {
                                if (!visibleMetrics.has(key)) return null;

                                const color = COLORS[idx % COLORS.length];

                                if (chartType === "area") {
                                    return (
                                        <Area
                                            key={key}
                                            type="monotone"
                                            dataKey={key}
                                            stroke={color}
                                            fill={color}
                                            fillOpacity={0.2}
                                            strokeWidth={2}
                                            dot={{ fill: color, r: 3 }}
                                            activeDot={{ r: 5 }}
                                        />
                                    );
                                } else {
                                    return (
                                        <Line
                                            key={key}
                                            type="monotone"
                                            dataKey={key}
                                            stroke={color}
                                            strokeWidth={2}
                                            dot={{ fill: color, r: 3 }}
                                            activeDot={{ r: 5 }}
                                        />
                                    );
                                }
                            })}
                        </ComposedChart>
                    </ResponsiveContainer>

                    {/* Additional Stats */}
                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                        {metricKeys.map((key) => {
                            const stat = stats[key];
                            return (
                                <div key={key} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                    <div>
                                        <p className="text-sm font-medium">{key}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-xs text-muted-foreground">
                                                Range: {stat.min.toFixed(3)} - {stat.max.toFixed(3)}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-lg font-bold">{stat.latest.toFixed(4)}</p>
                                        <p className="text-xs text-muted-foreground">Latest</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
