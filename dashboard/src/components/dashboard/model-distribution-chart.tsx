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
  // Calculate total for percentages
  const total = data && data.length > 0 ? data.reduce((sum, item) => sum + item.count, 0) : 0;

  // Format data for the pie chart
  const chartData = data && data.length > 0 ? data.map((item) => ({
    name: item.model,
    value: item.count,
  })) : [];

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold">Model Distribution</h3>
        <div className="text-[10px] text-muted-foreground">
          Total: {total}
        </div>
      </div>
      {!data || data.length === 0 ? (
        <div className="flex items-center justify-center h-[200px] text-xs text-muted-foreground">
          No model data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={(entry) => `${((entry.value / total) * 100).toFixed(1)}%`}
              outerRadius={65}
              dataKey="value"
              style={{ fontSize: '10px' }}
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
