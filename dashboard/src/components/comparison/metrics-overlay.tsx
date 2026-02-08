import { useMemo } from 'react';
import { useGroupedMetrics } from '../../hooks/use-metrics';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { format } from 'date-fns';

interface MetricsOverlayProps {
  experimentIds: string[];
}

const COLORS = [
  '#0ea5e9', // sky-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
];

export function MetricsOverlay({ experimentIds }: MetricsOverlayProps) {
  // Fetch metrics for all experiments
  const metricsQueries = experimentIds.map((id) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useGroupedMetrics(id)
  );

  const isLoading = metricsQueries.some((q) => q.isLoading);

  // Combine all metrics into a single dataset
  const chartData = useMemo(() => {
    if (isLoading) return [];

    const allMetrics: Record<string, unknown>[] = [];
    const timestampMap = new Map<string, Record<string, unknown>>();

    metricsQueries.forEach((query, expIndex) => {
      const groupedMetrics = query.data || {};

      Object.entries(groupedMetrics).forEach(([key, metrics]) => {
        metrics.forEach((metric) => {
          const timestamp = metric.createdAt;
          const dataKey = `exp${expIndex + 1}_${key}`;

          if (!timestampMap.has(timestamp)) {
            timestampMap.set(timestamp, {
              timestamp,
              time: format(new Date(timestamp), 'HH:mm:ss'),
            });
          }

          const dataPoint = timestampMap.get(timestamp)!;
          dataPoint[dataKey] = metric.value;
        });
      });
    });

    return Array.from(timestampMap.values()).sort((a, b) =>
      new Date(a.timestamp as string).getTime() -
      new Date(b.timestamp as string).getTime()
    );
  }, [metricsQueries, isLoading]);

  // Get all unique metric keys
  const metricKeys = useMemo(() => {
    const keys = new Set<string>();
    if (chartData.length > 0) {
      Object.keys(chartData[0]).forEach((key) => {
        if (key !== 'timestamp' && key !== 'time') {
          keys.add(key);
        }
      });
    }
    return Array.from(keys);
  }, [chartData]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Metrics Overlay</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-96 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Metrics Overlay</CardTitle>
          <CardDescription>
            Combined metrics visualization across experiments
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            No metrics data available for comparison
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Metrics Overlay</CardTitle>
        <CardDescription>
          Combined metrics from all selected experiments
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              label={{ value: 'Time', position: 'insideBottom', offset: -5 }}
            />
            <YAxis label={{ value: 'Value', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
            />
            <Legend />
            {metricKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
