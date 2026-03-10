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

  const successRate = useMemo(() => {
    const { totalSpans, successSpans } = traceStats;
    if (totalSpans === 0) return 0;
    return ((successSpans / totalSpans) * 100).toFixed(1);
  }, [traceStats]);

  const errorRate = useMemo(() => {
    const { totalSpans, errorSpans } = traceStats;
    if (totalSpans === 0) return 0;
    return ((errorSpans / totalSpans) * 100).toFixed(1);
  }, [traceStats]);

  if (traceStats.totalSpans === 0 || chartData.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        No trace data available
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Total Spans</dt>
          <dd className="mt-1.5 text-foreground font-mono text-sm">{traceStats.totalSpans.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Success Rate</dt>
          <dd className="mt-1.5 text-green-600 font-mono text-sm font-semibold">{successRate}%</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Error Rate</dt>
          <dd className="mt-1.5 text-red-600 font-mono text-sm font-semibold">{errorRate}%</dd>
        </div>
      </div>

      {/* Pie Chart */}
      <ResponsiveContainer width="100%" height={180}>
        <PieChart margin={{ top: 20, bottom: 5 }}>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="48%"
            outerRadius={48}
            label={({ name, value }) => `${name}: ${value}`}
            style={{ fontSize: '10px' }}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
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
    </div>
  );
}
