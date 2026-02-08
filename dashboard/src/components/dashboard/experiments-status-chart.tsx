import { useMemo } from 'react';
import { TeamExperiment } from '../../hooks/use-team-experiments';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';

interface ExperimentsStatusChartProps {
  experiments: TeamExperiment[];
}

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: '#22c55e',
  RUNNING: '#3b82f6',
  FAILED: '#ef4444',
  PENDING: '#eab308',
  CANCELLED: '#6b7280',
  UNKNOWN: '#9ca3af',
};

export function ExperimentsStatusChart({ experiments }: ExperimentsStatusChartProps) {
  const chartData = useMemo(() => {
    const statusMap = new Map<string, number>();

    experiments.forEach((exp) => {
      const status = exp.status;
      const current = statusMap.get(status) || 0;
      statusMap.set(status, current + 1);
    });

    return Array.from(statusMap.entries())
      .map(([status, count]) => ({
        name: status,
        value: count,
        color: STATUS_COLORS[status] || STATUS_COLORS.UNKNOWN,
      }))
      .sort((a, b) => b.value - a.value); // Sort by count descending
  }, [experiments]);

  if (chartData.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Experiments Distribution</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={65}
            label={({ name, value }) => `${name}: ${value}`}
            style={{ fontSize: '12px' }}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
