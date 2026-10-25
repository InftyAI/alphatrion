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
  ABORTED: '#9ca3af',
  UNKNOWN: '#a78bfa',
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

  // Calculate total for percentages
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold">Experiments Distribution</h3>
        <div className="text-[10px] text-muted-foreground">
          Total: {total}
        </div>
      </div>
      {chartData.length === 0 ? (
        <div className="flex items-center justify-center h-[200px] text-xs text-muted-foreground">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={65}
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
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
                fontSize: '10px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
