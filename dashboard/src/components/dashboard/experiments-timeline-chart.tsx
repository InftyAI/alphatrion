import { useMemo } from 'react';
import { TeamExperiment } from '../../hooks/use-team-experiments';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, subDays, subMonths, startOfDay, endOfDay } from 'date-fns';

interface ExperimentsTimelineChartProps {
  experiments: TeamExperiment[];
  timeRange: '7days' | '1month' | '3months';
}

type TimeRange = '7days' | '1month' | '3months';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days: number }[] = [
  { value: '7days', label: '7 Days', days: 7 },
  { value: '1month', label: '1 Month', days: 30 },
  { value: '3months', label: '3 Months', days: 90 },
];

export function ExperimentsTimelineChart({ experiments, timeRange }: ExperimentsTimelineChartProps) {

  const chartData = useMemo(() => {
    const selectedRange = TIME_RANGE_OPTIONS.find((r) => r.value === timeRange);
    if (!selectedRange) return [];

    const now = new Date();

    // Create date map for aggregation
    const dateMap = new Map<string, number>();

    // Initialize all dates in range with 0
    for (let i = 0; i < selectedRange.days; i++) {
      const date = subDays(now, selectedRange.days - 1 - i);
      const dateKey = format(startOfDay(date), 'yyyy-MM-dd');
      dateMap.set(dateKey, 0);
    }

    // Count experiments per day (experiments are already filtered by parent)
    experiments.forEach((exp) => {
      const expDate = new Date(exp.createdAt);
      const dateKey = format(startOfDay(expDate), 'yyyy-MM-dd');
      const current = dateMap.get(dateKey) || 0;
      dateMap.set(dateKey, current + 1);
    });

    // Convert to array and format for chart
    return Array.from(dateMap.entries())
      .map(([date, count]) => ({
        date,
        experiments: count,
        displayDate: format(new Date(date), 'MMM dd'),
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [experiments, timeRange]);

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Experiments Timeline</h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            width={60}
            label={{
              value: 'Count',
              angle: -90,
              position: 'insideLeft',
              style: { textAnchor: 'middle' }
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
            }}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="experiments"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--primary))', r: 4 }}
            activeDot={{ r: 6 }}
            name="Experiments Launched"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
