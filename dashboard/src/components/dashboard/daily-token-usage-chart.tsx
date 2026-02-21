import { useMemo } from 'react';
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
import { format, subDays, startOfDay } from 'date-fns';
import type { DailyTokenUsage } from '../../hooks/use-token-usage';

interface DailyTokenUsageChartProps {
  data: DailyTokenUsage[];
  timeRange: '7days' | '1month' | '3months';
}

type TimeRange = '7days' | '1month' | '3months';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days: number }[] = [
  { value: '7days', label: '7 Days', days: 7 },
  { value: '1month', label: '1 Month', days: 30 },
  { value: '3months', label: '3 Months', days: 90 },
];

export function DailyTokenUsageChart({ data, timeRange }: DailyTokenUsageChartProps) {
  const chartData = useMemo(() => {
    const selectedRange = TIME_RANGE_OPTIONS.find((r) => r.value === timeRange);
    if (!selectedRange) return [];

    const now = new Date();

    // Create date map for aggregation - fill all dates with 0
    const dateMap = new Map<string, { totalTokens: number; inputTokens: number; outputTokens: number }>();

    // Initialize all dates in range with 0
    for (let i = 0; i < selectedRange.days; i++) {
      const date = subDays(now, selectedRange.days - 1 - i);
      const dateKey = format(startOfDay(date), 'yyyy-MM-dd');
      dateMap.set(dateKey, { totalTokens: 0, inputTokens: 0, outputTokens: 0 });
    }

    // Fill in actual data
    data.forEach((item) => {
      const dateKey = format(new Date(item.date), 'yyyy-MM-dd');
      if (dateMap.has(dateKey)) {
        dateMap.set(dateKey, {
          totalTokens: item.totalTokens,
          inputTokens: item.inputTokens,
          outputTokens: item.outputTokens,
        });
      }
    });

    // Convert to array and format for chart
    return Array.from(dateMap.entries())
      .map(([date, tokens]) => ({
        date,
        displayDate: format(new Date(date), 'MMM dd'),
        totalTokens: tokens.totalTokens,
        inputTokens: tokens.inputTokens,
        outputTokens: tokens.outputTokens,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [data, timeRange]);

  // Calculate total tokens across all days
  const totalTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.totalTokens, 0);
  }, [chartData]);

  const totalInputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.inputTokens, 0);
  }, [chartData]);

  const totalOutputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.outputTokens, 0);
  }, [chartData]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Token Usage</h3>
        <div className="text-xs text-muted-foreground">
          Total: {totalTokens.toLocaleString()} ({totalInputTokens.toLocaleString()}↓ {totalOutputTokens.toLocaleString()}↑)
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ left: 0, right: 15, top: 15, bottom: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={70}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            width={40}
            tickFormatter={(value) =>
              value >= 1000000
                ? `${(value / 1000000).toFixed(1)}M`
                : value >= 1000
                ? `${(value / 1000).toFixed(1)}K`
                : value.toString()
            }
            label={{
              value: 'Tokens',
              angle: -90,
              position: 'insideLeft',
              offset: 8,
              style: { textAnchor: 'middle', fontSize: 11 }
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '12px',
            }}
            content={({ active, payload, label }) => {
              if (!active || !payload || !payload.length) return null;
              const data = payload[0].payload;
              return (
                <div className="bg-card border border-border rounded-md p-2 shadow-sm">
                  <div className="text-xs font-medium mb-1.5">{label}</div>
                  <div className="space-y-0.5 text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      <span className="text-muted-foreground">Total:</span>
                      <span className="font-medium ml-auto">{data.totalTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500"></div>
                      <span className="text-muted-foreground">Input:</span>
                      <span className="font-medium ml-auto">{data.inputTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                      <span className="text-muted-foreground">Output:</span>
                      <span className="font-medium ml-auto">{data.outputTokens.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              );
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '11px' }}
            iconType="circle"
            iconSize={8}
          />
          <Line
            type="monotone"
            dataKey="totalTokens"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 3 }}
            activeDot={{ r: 5 }}
            name="Total"
          />
          <Line
            type="monotone"
            dataKey="inputTokens"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', r: 3 }}
            activeDot={{ r: 5 }}
            name="Input"
          />
          <Line
            type="monotone"
            dataKey="outputTokens"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 3 }}
            activeDot={{ r: 5 }}
            name="Output"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
