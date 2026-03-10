import { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { Run } from '../../types';

interface RunStatusChartProps {
  runs: Run[];
}

export function RunStatusChart({ runs }: RunStatusChartProps) {
  const chartData = useMemo(() => {
    if (!runs || runs.length === 0) return [];

    const stats = [
      { name: 'COMPLETED', value: runs.filter(r => r.status === 'COMPLETED').length, color: '#22c55e' },
      { name: 'RUNNING', value: runs.filter(r => r.status === 'RUNNING').length, color: '#3b82f6' },
      { name: 'FAILED', value: runs.filter(r => r.status === 'FAILED').length, color: '#ef4444' },
      { name: 'PENDING', value: runs.filter(r => r.status === 'PENDING').length, color: '#eab308' },
      { name: 'CANCELLED', value: runs.filter(r => r.status === 'CANCELLED').length, color: '#6b7280' },
      { name: 'UNKNOWN', value: runs.filter(r => r.status === 'UNKNOWN').length, color: '#a78bfa' },
    ];

    return stats.filter(s => s.value > 0);
  }, [runs]);

  // Calculate total for percentages
  const total = runs.length;

  if (runs.length === 0 || chartData.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-xs text-muted-foreground">
        No run data available
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
          formatter={(value: number) => [value, 'Count']}
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
