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
import type { DailyCostUsage } from '../../hooks/use-cost-usage';

interface DailyCostUsageChartProps {
  data: DailyCostUsage[];
  timeRange: '7days' | '1month' | '3months';
}

type TimeRange = '7days' | '1month' | '3months';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days: number }[] = [
  { value: '7days', label: '7 Days', days: 7 },
  { value: '1month', label: '1 Month', days: 30 },
  { value: '3months', label: '3 Months', days: 90 },
];

export function DailyCostUsageChart({ data, timeRange }: DailyCostUsageChartProps) {
  const chartData = useMemo(() => {
    const selectedRange = TIME_RANGE_OPTIONS.find((r) => r.value === timeRange);
    if (!selectedRange) return [];

    const now = new Date();

    // Create date map for aggregation - fill all dates with 0
    const dateMap = new Map<string, {
      totalCost: number;
      totalTokens: number;
      inputTokens: number;
      outputTokens: number;
      cacheReadInputTokens: number;
      cacheCreationInputTokens: number;
    }>();

    // Initialize all dates in range with 0
    for (let i = 0; i < selectedRange.days; i++) {
      const date = subDays(now, selectedRange.days - 1 - i);
      const dateKey = format(startOfDay(date), 'yyyy-MM-dd');
      dateMap.set(dateKey, {
        totalCost: 0,
        totalTokens: 0,
        inputTokens: 0,
        outputTokens: 0,
        cacheReadInputTokens: 0,
        cacheCreationInputTokens: 0,
      });
    }

    // Fill in actual data
    data.forEach((item) => {
      const dateKey = format(new Date(item.date), 'yyyy-MM-dd');
      if (dateMap.has(dateKey)) {
        dateMap.set(dateKey, {
          totalCost: item.totalCost,
          totalTokens: item.totalTokens,
          inputTokens: item.inputTokens,
          outputTokens: item.outputTokens,
          cacheReadInputTokens: item.cacheReadInputTokens,
          cacheCreationInputTokens: item.cacheCreationInputTokens,
        });
      }
    });

    // Convert to array and format for chart
    return Array.from(dateMap.entries())
      .map(([date, values]) => ({
        date,
        displayDate: format(new Date(date), 'MMM dd'),
        totalCost: values.totalCost,
        totalTokens: values.totalTokens,
        inputTokens: values.inputTokens,
        outputTokens: values.outputTokens,
        cacheReadInputTokens: values.cacheReadInputTokens,
        cacheCreationInputTokens: values.cacheCreationInputTokens,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [data, timeRange]);

  // Calculate totals across all days
  const totalCost = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.totalCost, 0);
  }, [chartData]);

  const totalTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.totalTokens, 0);
  }, [chartData]);

  const totalInputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.inputTokens, 0);
  }, [chartData]);

  const totalOutputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.outputTokens, 0);
  }, [chartData]);

  const totalCacheReadInputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.cacheReadInputTokens, 0);
  }, [chartData]);

  const totalCacheCreationInputTokens = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.cacheCreationInputTokens, 0);
  }, [chartData]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold">Cost & Token Usage</h3>
        <div className="text-[10px] text-muted-foreground">
          ${totalCost.toFixed(4)} • {totalTokens.toLocaleString()} tokens (in:{totalInputTokens.toLocaleString()} out:{totalOutputTokens.toLocaleString()} cache-r:{totalCacheReadInputTokens.toLocaleString()} cache-c:{totalCacheCreationInputTokens.toLocaleString()})
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ left: 5, right: 45, top: 5, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 9 }}
            angle={-45}
            textAnchor="end"
            height={40}
          />
          {/* Left Y-Axis for Tokens */}
          <YAxis
            yAxisId="tokens"
            tick={{ fontSize: 9 }}
            width={40}
            tickFormatter={(value) => {
              if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
              if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
              return value.toString();
            }}
            label={{
              value: 'Tokens',
              angle: -90,
              position: 'insideLeft',
              offset: 0,
              style: { textAnchor: 'middle', fontSize: 9 }
            }}
          />
          {/* Right Y-Axis for Cost */}
          <YAxis
            yAxisId="cost"
            orientation="right"
            tick={{ fontSize: 9 }}
            width={45}
            tickFormatter={(value) =>
              value >= 1
                ? `$${value.toFixed(2)}`
                : value >= 0.01
                ? `$${value.toFixed(3)}`
                : `$${value.toFixed(4)}`
            }
            label={{
              value: 'Cost (USD)',
              angle: 90,
              position: 'insideRight',
              offset: 0,
              style: { textAnchor: 'middle', fontSize: 9 }
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '10px',
            }}
            content={({ active, payload, label }) => {
              if (!active || !payload || !payload.length) return null;
              const data = payload[0].payload;
              return (
                <div className="bg-card border border-border rounded-md p-2 shadow-sm">
                  <div className="text-[10px] font-medium mb-1.5">{label}</div>
                  <div className="space-y-0.5 text-[10px]">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                      <span className="text-muted-foreground">Cost:</span>
                      <span className="font-medium ml-auto">${data.totalCost.toFixed(4)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      <span className="text-muted-foreground">Total Tokens:</span>
                      <span className="font-medium ml-auto">{data.totalTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                      <span className="text-muted-foreground">Input:</span>
                      <span className="font-medium ml-auto">{data.inputTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                      <span className="text-muted-foreground">Output:</span>
                      <span className="font-medium ml-auto">{data.outputTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-cyan-500"></div>
                      <span className="text-muted-foreground">Cache Read:</span>
                      <span className="font-medium ml-auto">{data.cacheReadInputTokens.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                      <span className="text-muted-foreground">Cache Creation:</span>
                      <span className="font-medium ml-auto">{data.cacheCreationInputTokens.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              );
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '10px', paddingTop: '2px' }}
            iconType="circle"
            iconSize={6}
            verticalAlign="bottom"
            height={20}
          />
          {/* Token Lines - Left Y-Axis */}
          <Line
            yAxisId="tokens"
            type="monotone"
            dataKey="totalTokens"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 3 }}
            activeDot={{ r: 5 }}
            name="Total Tokens"
          />
          <Line
            yAxisId="tokens"
            type="monotone"
            dataKey="inputTokens"
            stroke="#a855f7"
            strokeWidth={2}
            dot={{ fill: '#a855f7', r: 3 }}
            activeDot={{ r: 5 }}
            name="Input"
          />
          <Line
            yAxisId="tokens"
            type="monotone"
            dataKey="outputTokens"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 3 }}
            activeDot={{ r: 5 }}
            name="Output"
          />
          <Line
            yAxisId="tokens"
            type="monotone"
            dataKey="cacheReadInputTokens"
            stroke="#06b6d4"
            strokeWidth={2}
            dot={{ fill: '#06b6d4', r: 3 }}
            activeDot={{ r: 5 }}
            name="Cache Read"
          />
          <Line
            yAxisId="tokens"
            type="monotone"
            dataKey="cacheCreationInputTokens"
            stroke="#ec4899"
            strokeWidth={2}
            dot={{ fill: '#ec4899', r: 3 }}
            activeDot={{ r: 5 }}
            name="Cache Creation"
          />
          {/* Cost Line - Right Y-Axis */}
          <Line
            yAxisId="cost"
            type="monotone"
            dataKey="totalCost"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', r: 3 }}
            activeDot={{ r: 5 }}
            name="Cost"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
