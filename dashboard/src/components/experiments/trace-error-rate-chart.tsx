import { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { TraceStats } from '../../types';

interface TraceErrorRateChartProps {
  traceStats: TraceStats;
}

export function TraceErrorRateChart({ traceStats }: TraceErrorRateChartProps) {
  const chartData = useMemo(() => {
    const { successSpans, errorSpans } = traceStats;

    const data = [];
    if (successSpans > 0) {
      data.push({ name: 'Success', value: successSpans, color: '#22c55e' });
    }
    if (errorSpans > 0) {
      data.push({ name: 'Error', value: errorSpans, color: '#ef4444' });
    }

    return data;
  }, [traceStats]);

  // Calculate total for percentages
  const total = traceStats.totalSpans;

  if (traceStats.totalSpans === 0 || chartData.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-xs text-muted-foreground">
        No trace data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={70}
          labelLine={false}
          label={(entry) => `${((entry.value / total) * 100).toFixed(1)}%`}
          style={{ fontSize: '10px' }}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [value, 'Spans']}
          contentStyle={{
            fontSize: '10px',
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '6px',
          }}
        />
        <Legend wrapperStyle={{ fontSize: '10px' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
