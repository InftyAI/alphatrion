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

  // Calculate total experiments in the time range
  const totalExperiments = useMemo(() => {
    return experiments.length;
  }, [experiments]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Experiments Timeline</h3>
        <div className="text-xs text-muted-foreground">
          Total: {totalExperiments}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ left: 0, right: 15, top: 15, bottom: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={70}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            width={40}
            label={{
              value: 'Count',
              angle: -90,
              position: 'insideLeft',
              offset: 8,
              style: { textAnchor: 'middle', fontSize: 11 }
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
                      <div className="w-2 h-2 rounded-full bg-purple-400"></div>
                      <span className="text-muted-foreground">Launched:</span>
                      <span className="font-medium ml-auto">{data.experiments}</span>
                    </div>
                  </div>
                </div>
              );
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '10px' }}
            iconType="circle"
            iconSize={8}
          />
          <Line
            type="monotone"
            dataKey="experiments"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={{ fill: '#a78bfa', r: 3 }}
            activeDot={{ r: 5 }}
            name="Launched"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
