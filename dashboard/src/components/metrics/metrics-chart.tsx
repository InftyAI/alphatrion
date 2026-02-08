import { useMemo, useState } from 'react';
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
import { Badge } from '../ui/badge';
import type { Metric, GroupedMetrics } from '../../types';
import { format } from 'date-fns';

interface MetricsChartProps {
  metrics: GroupedMetrics;
  title?: string;
  description?: string;
}

// Generate colors for different metric keys
const COLORS = [
  '#0ea5e9', // sky-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#ef4444', // red-500
  '#6366f1', // indigo-500
  '#14b8a6', // teal-500
];

export function MetricsChart({ metrics, title = 'Metrics', description }: MetricsChartProps) {
  const metricKeys = Object.keys(metrics);
  const [selectedKey, setSelectedKey] = useState<string>(
    metricKeys[0] || '' // Select first metric by default
  );

  // Transform metrics data for Recharts
  const chartData = useMemo(() => {
    if (metricKeys.length === 0 || !selectedKey) return [];

    // Collect all data points for the selected metric
    const dataPoints: Array<{
      timestamp: number;
      index: number;
      time: string;
      value: number;
      runId: string;
    }> = [];

    if (metrics[selectedKey]) {
      metrics[selectedKey].forEach((metric, index) => {
        if (metric.value !== null) {
          dataPoints.push({
            timestamp: new Date(metric.createdAt).getTime(),
            index,  // Sequential index for X-axis
            time: format(new Date(metric.createdAt), 'MMM dd HH:mm:ss'),
            value: metric.value,
            runId: metric.runId,
          });
        }
      });
    }

    // Sort by timestamp chronologically
    dataPoints.sort((a, b) => a.timestamp - b.timestamp);

    // Update indices after sorting
    dataPoints.forEach((point, index) => {
      point.index = index;
    });

    // Debug logging
    console.log('[MetricsChart] Selected key:', selectedKey);
    console.log('[MetricsChart] Total metrics for this key:', metrics[selectedKey]?.length);
    console.log('[MetricsChart] Total data points after processing:', dataPoints.length);
    console.log('[MetricsChart] All data points:', dataPoints);

    return dataPoints;
  }, [metrics, metricKeys, selectedKey]);

  const selectKey = (key: string) => {
    setSelectedKey(key);
  };

  if (metricKeys.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            No metrics data available
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}

        {/* Metric key selector - Single selection */}
        <div className="flex flex-wrap gap-2 pt-4">
          {metricKeys.map((key, index) => (
            <Badge
              key={key}
              variant={selectedKey === key ? 'default' : 'outline'}
              className="cursor-pointer"
              style={{
                backgroundColor: selectedKey === key
                  ? COLORS[index % COLORS.length]
                  : undefined,
              }}
              onClick={() => selectKey(key)}
            >
              {key}
            </Badge>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {!selectedKey ? (
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            Select a metric to display
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="index"
                label={{ value: 'Index', position: 'insideBottom', offset: -5 }}
                type="number"
                domain={['dataMin', 'dataMax']}
              />
              <YAxis label={{ value: 'Value', angle: -90, position: 'insideLeft' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '0.5rem',
                }}
                formatter={(value: any, name: string, props: any) => {
                  return [value, 'Value'];
                }}
                labelFormatter={(value, payload) => {
                  if (payload && payload[0] && payload[0].payload) {
                    const point = payload[0].payload;
                    return `Run: ${point.runId}\nTime: ${point.time}`;
                  }
                  return value;
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                name={selectedKey}
                stroke={COLORS[metricKeys.indexOf(selectedKey) % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
