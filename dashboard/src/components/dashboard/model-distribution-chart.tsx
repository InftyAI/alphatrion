import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import type { ModelDistribution } from '../../hooks/use-model-distributions';

interface ModelDistributionChartProps {
  data: ModelDistribution[];
}

// Color palette for the pie chart
const COLORS = [
  '#8b5cf6', // purple
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
];

export function ModelDistributionChart({ data }: ModelDistributionChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 text-sm text-muted-foreground">
        No model data available
      </div>
    );
  }

  // Calculate total for percentages
  const total = data.reduce((sum, item) => sum + item.count, 0);

  // Format data for the pie chart
  const chartData = data.map((item) => ({
    name: item.model,
    value: item.count,
  }));

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">Model Distribution</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(entry) => `${((entry.value / total) * 100).toFixed(1)}%`}
            outerRadius={75}
            dataKey="value"
            style={{ fontSize: '11px' }}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [value, 'Count']}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '11px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
