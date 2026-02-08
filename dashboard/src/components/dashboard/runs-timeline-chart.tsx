import { useMemo, useState } from 'react';
import { TeamRun } from '../../hooks/use-team-runs';
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
import { Button } from '../ui/button';
import { format, subDays, subMonths, startOfDay, endOfDay } from 'date-fns';

interface RunsTimelineChartProps {
  runs: TeamRun[];
}

type TimeRange = '7days' | '1month' | '3months';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days: number }[] = [
  { value: '7days', label: '7 Days', days: 7 },
  { value: '1month', label: '1 Month', days: 30 },
  { value: '3months', label: '3 Months', days: 90 },
];

export function RunsTimelineChart({ runs }: RunsTimelineChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('7days');

  const chartData = useMemo(() => {
    const selectedRange = TIME_RANGE_OPTIONS.find((r) => r.value === timeRange);
    if (!selectedRange) return [];

    const now = new Date();
    const startDate =
      timeRange === '7days'
        ? subDays(now, 7)
        : timeRange === '1month'
        ? subMonths(now, 1)
        : subMonths(now, 3);

    // Filter runs within the time range
    const filteredRuns = runs.filter((run) => {
      const runDate = new Date(run.createdAt);
      return runDate >= startDate && runDate <= now;
    });

    // Create date map for aggregation
    const dateMap = new Map<string, number>();

    // Initialize all dates in range with 0
    for (let i = 0; i < selectedRange.days; i++) {
      const date = subDays(now, selectedRange.days - 1 - i);
      const dateKey = format(startOfDay(date), 'yyyy-MM-dd');
      dateMap.set(dateKey, 0);
    }

    // Count runs per day
    filteredRuns.forEach((run) => {
      const runDate = new Date(run.createdAt);
      const dateKey = format(startOfDay(runDate), 'yyyy-MM-dd');
      const current = dateMap.get(dateKey) || 0;
      dateMap.set(dateKey, current + 1);
    });

    // Convert to array and format for chart
    return Array.from(dateMap.entries())
      .map(([date, count]) => ({
        date,
        runs: count,
        displayDate: format(new Date(date), 'MMM dd'),
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [runs, timeRange]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Runs Timeline</h3>
        <div className="flex gap-2">
          {TIME_RANGE_OPTIONS.map((option) => (
            <Button
              key={option.value}
              variant={timeRange === option.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimeRange(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
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
            label={{ value: 'Number of Runs', angle: -90, position: 'insideLeft' }}
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
            dataKey="runs"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--primary))', r: 4 }}
            activeDot={{ r: 6 }}
            name="Runs Launched"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
