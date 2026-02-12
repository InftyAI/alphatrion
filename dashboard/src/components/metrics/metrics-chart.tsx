import { useMemo, useState, lazy, Suspense } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
  ComposedChart,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import type { Metric, GroupedMetrics, MetricConfig } from '../../types';
import { format } from 'date-fns';
import { useRunMetrics } from '../../hooks/use-run-metrics';
import { calculateParetoFrontier } from '../../lib/pareto';
import { X } from 'lucide-react';

// Lazy load Plotly for 3D visualization to reduce bundle size
const Plot = lazy(() => import('react-plotly.js'));

interface MetricsChartProps {
  metrics: GroupedMetrics;
  experimentId: string;
  title?: string;
  description?: string;
}

// Generate colors for different metric keys
const COLORS = [
  '#0ea5e9', // sky-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#ef4444', // red-500
  '#6366f1', // indigo-500
  '#14b8a6', // teal-500
];

const PARETO_COLOR = '#10b981'; // emerald-500
const PARETO_COLOR_LIGHT = '#34d399'; // emerald-400
const DOMINATED_COLOR = '#9ca3af'; // gray-400
const GRID_COLOR = '#f3f4f6'; // gray-100

export function MetricsChart({ metrics, experimentId, title = 'Metrics', description }: MetricsChartProps) {
  const metricKeys = Object.keys(metrics);
  const [selectedKey, setSelectedKey] = useState<string>(
    metricKeys[0] || '' // Select first metric by default
  );
  const [viewMode, setViewMode] = useState<'timeline' | 'pareto'>('timeline');
  const [paretoMetrics, setParetoMetrics] = useState<MetricConfig[]>([]);

  const { runMetrics, availableMetrics } = useRunMetrics(experimentId);

  // Filter runs for Pareto analysis
  const filteredRunMetrics = useMemo(() => {
    if (paretoMetrics.length === 0) return runMetrics;
    return runMetrics.filter((run) =>
      paretoMetrics.every((config) => run.metrics[config.key] !== undefined)
    );
  }, [runMetrics, paretoMetrics]);

  // Calculate Pareto frontier
  const paretoRunIds = useMemo(() => {
    if (paretoMetrics.length < 2 || filteredRunMetrics.length < 2) {
      return new Set<string>();
    }
    return calculateParetoFrontier(filteredRunMetrics, paretoMetrics);
  }, [filteredRunMetrics, paretoMetrics]);

  // Transform metrics data for Recharts
  const chartData = useMemo(() => {
    if (metricKeys.length === 0 || !selectedKey) return [];

    // Collect all data points for the selected metric
    const dataPoints: Array<{
      timestamp: number;
      index: number;
      time: string;
      value: number;
      runId: string;
    }> = [];

    if (metrics[selectedKey]) {
      metrics[selectedKey].forEach((metric, index) => {
        if (metric.value !== null) {
          dataPoints.push({
            timestamp: new Date(metric.createdAt).getTime(),
            index,  // Sequential index for X-axis
            time: format(new Date(metric.createdAt), 'MMM dd HH:mm:ss'),
            value: metric.value,
            runId: metric.runId,
          });
        }
      });
    }

    // Sort by timestamp chronologically
    dataPoints.sort((a, b) => a.timestamp - b.timestamp);

    // Update indices after sorting
    dataPoints.forEach((point, index) => {
      point.index = index;
    });

    // Debug logging
    console.log('[MetricsChart] Selected key:', selectedKey);
    console.log('[MetricsChart] Total metrics for this key:', metrics[selectedKey]?.length);
    console.log('[MetricsChart] Total data points after processing:', dataPoints.length);
    console.log('[MetricsChart] All data points:', dataPoints);

    return dataPoints;
  }, [metrics, metricKeys, selectedKey]);

  // Pareto scatter chart data
  const paretoChartData = useMemo(() => {
    if (paretoMetrics.length < 2) return { all: [], paretoLine: [] };

    const xMetric = paretoMetrics[0];
    const yMetric = paretoMetrics[1];
    const zMetric = paretoMetrics.length >= 3 ? paretoMetrics[2] : undefined;

    const allPoints = filteredRunMetrics.map((run) => ({
      runId: run.runId,
      x: run.metrics[xMetric.key],
      y: run.metrics[yMetric.key],
      z: zMetric ? run.metrics[zMetric.key] : undefined,
      isParetoOptimal: paretoRunIds.has(run.runId),
      metrics: run.metrics,
    }));

    // Sort Pareto optimal points by x-axis for line connection
    const paretoPoints = allPoints
      .filter((p) => p.isParetoOptimal)
      .sort((a, b) => a.x - b.x);

    return { all: allPoints, paretoLine: paretoPoints };
  }, [filteredRunMetrics, paretoMetrics, paretoRunIds]);

  // Prepare 3D Plotly data
  const plotly3DData = useMemo(() => {
    if (paretoMetrics.length !== 3 || paretoChartData.all.length === 0) return null;

    // For 3D, sort Pareto points by x, then y, then z for a coherent line
    const paretoPoints = [...paretoChartData.paretoLine].sort((a, b) => {
      if (a.x !== b.x) return a.x - b.x;
      if (a.y !== b.y) return a.y - b.y;
      return (a.z || 0) - (b.z || 0);
    });

    const dominatedPoints = paretoChartData.all.filter((d) => !d.isParetoOptimal);

    const traces: any[] = [
      {
        x: dominatedPoints.map((d) => d.x),
        y: dominatedPoints.map((d) => d.y),
        z: dominatedPoints.map((d) => d.z),
        mode: 'markers',
        type: 'scatter3d',
        name: 'Dominated',
        showlegend: false,
        marker: {
          size: 6,
          color: DOMINATED_COLOR,
          opacity: 0.4,
          symbol: 'circle',
          line: {
            color: '#6b7280',
            width: 1,
            opacity: 0.3,
          },
        },
        customdata: dominatedPoints.map((d) => [d.runId.slice(0, 8) + '...', d.x, d.y, d.z, d.runId]),
        hovertemplate:
          '<b>Run: %{customdata[0]}</b>' +
          '<br>' + `${paretoMetrics[0].key}: %{customdata[1]:.4f}` +
          '<br>' + `${paretoMetrics[1].key}: %{customdata[2]:.4f}` +
          '<br>' + `${paretoMetrics[2].key}: %{customdata[3]:.4f}` +
          '<extra></extra>',
        hoverlabel: {
          bgcolor: '#fafafa',
          bordercolor: '#d1d5db',
          font: {
            family: 'system-ui, -apple-system, sans-serif',
            size: 12,
            color: '#374151',
          },
          align: 'left',
        },
      },
      {
        x: paretoPoints.map((d) => d.x),
        y: paretoPoints.map((d) => d.y),
        z: paretoPoints.map((d) => d.z),
        mode: 'markers',
        type: 'scatter3d',
        name: 'Pareto Optimal',
        showlegend: false,
        marker: {
          size: 9,
          color: PARETO_COLOR,
          symbol: 'circle',
          opacity: 0.95,
          line: {
            color: '#059669',
            width: 2,
            opacity: 0.8,
          },
        },
        customdata: paretoPoints.map((d) => [d.runId.slice(0, 8) + '...', d.x, d.y, d.z, d.runId]),
        hovertemplate:
          '<b>Run: %{customdata[0]}</b>' +
          '<br>' + `${paretoMetrics[0].key}: %{customdata[1]:.4f}` +
          '<br>' + `${paretoMetrics[1].key}: %{customdata[2]:.4f}` +
          '<br>' + `${paretoMetrics[2].key}: %{customdata[3]:.4f}` +
          '<extra></extra>',
        hoverlabel: {
          bgcolor: '#f0fdf4',
          bordercolor: '#86efac',
          font: {
            family: 'system-ui, -apple-system, sans-serif',
            size: 12,
            color: '#374151',
          },
          align: 'left',
        },
      },
    ];

    // Add lines connecting Pareto optimal points if more than one
    if (paretoPoints.length > 1) {
      traces.push({
        x: paretoPoints.map((d) => d.x),
        y: paretoPoints.map((d) => d.y),
        z: paretoPoints.map((d) => d.z),
        mode: 'lines',
        type: 'scatter3d',
        name: 'Pareto Frontier',
        showlegend: false,
        line: {
          color: PARETO_COLOR,
          width: 5,
        },
        hoverinfo: 'skip',
      });
    }

    return traces;
  }, [paretoChartData, paretoMetrics]);

  const selectKey = (key: string) => {
    setSelectedKey(key);
  };

  const handleAddParetoMetric = (key: string) => {
    if (paretoMetrics.length >= 3 || paretoMetrics.some((m) => m.key === key)) return;
    setParetoMetrics([...paretoMetrics, { key, direction: 'maximize' }]);
  };

  const handleRemoveParetoMetric = (key: string) => {
    setParetoMetrics(paretoMetrics.filter((m) => m.key !== key));
  };

  const handleToggleDirection = (key: string) => {
    setParetoMetrics(
      paretoMetrics.map((m) =>
        m.key === key ? { ...m, direction: m.direction === 'maximize' ? 'minimize' : 'maximize' } : m
      )
    );
  };

  if (metricKeys.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">{title}</CardTitle>
          {description && <CardDescription className="text-xs">{description}</CardDescription>}
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            No metrics data available
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-sm">{title}</CardTitle>
            {description && <CardDescription className="text-xs">{description}</CardDescription>}
          </div>
          {/* View mode toggle */}
          <div className="flex gap-1">
            <Button
              variant={viewMode === 'timeline' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('timeline')}
              className="h-7 px-3 text-xs"
            >
              Timeline
            </Button>
            <Button
              variant={viewMode === 'pareto' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('pareto')}
              className="h-7 px-3 text-xs"
            >
              Pareto
            </Button>
          </div>
        </div>

        {viewMode === 'timeline' ? (
          /* Timeline view - Metric key selector */
          <div className="flex flex-wrap gap-1.5 pt-3">
            {metricKeys.map((key, index) => (
              <Badge
                key={key}
                variant={selectedKey === key ? 'default' : 'outline'}
                className="cursor-pointer text-xs px-2 py-0.5"
                style={{
                  backgroundColor: selectedKey === key
                    ? COLORS[index % COLORS.length]
                    : undefined,
                }}
                onClick={() => selectKey(key)}
              >
                {key}
              </Badge>
            ))}
          </div>
        ) : (
          /* Pareto view - Metric selector */
          <div className="space-y-2 pt-3">
            <div className="flex flex-wrap gap-1.5">
              {availableMetrics.map((key, index) => {
                const selected = paretoMetrics.find((m) => m.key === key);
                const isMaximize = selected?.direction === 'maximize';

                return (
                  <Badge
                    key={key}
                    variant={selected ? 'default' : 'outline'}
                    className="cursor-pointer text-xs px-2 py-1 transition-colors relative"
                    style={{
                      backgroundColor: selected
                        ? COLORS[index % COLORS.length]
                        : undefined,
                      borderColor: selected
                        ? COLORS[index % COLORS.length]
                        : undefined,
                    }}
                    onClick={() => {
                      if (selected) {
                        // If already selected, toggle direction
                        handleToggleDirection(key);
                      } else if (paretoMetrics.length < 3) {
                        // If not selected and under limit, add it
                        handleAddParetoMetric(key);
                      }
                    }}
                    onContextMenu={(e) => {
                      // Right-click to remove
                      e.preventDefault();
                      if (selected) {
                        handleRemoveParetoMetric(key);
                      }
                    }}
                  >
                    {key}
                    {selected && (
                      <span className="ml-1 text-[10px] opacity-90">
                        {isMaximize ? '↑' : '↓'}
                      </span>
                    )}
                  </Badge>
                );
              })}
            </div>
            {paretoMetrics.length > 0 && (
              <div className="text-xs text-gray-500 italic">
                Click: toggle direction ↑↓ • Right-click: remove
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              {paretoMetrics.length === 0 ? (
                <span>Click metrics to select (up to 3)</span>
              ) : paretoMetrics.length < 2 ? (
                <span>Select at least 2 metrics for analysis</span>
              ) : (
                <div className="flex items-center gap-4">
                  <span>Runs: {filteredRunMetrics.length}</span>
                  {paretoRunIds.size > 0 && (
                    <span className="text-emerald-600 font-medium">Pareto Optimal: {paretoRunIds.size}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="pt-0">
        {viewMode === 'timeline' ? (
          /* Timeline Chart */
          !selectedKey ? (
            <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
              Select a metric to display
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                onClick={(data: any) => {
                  if (data && data.activePayload && data.activePayload[0]) {
                    const point = data.activePayload[0].payload;
                    if (point.runId) {
                      window.open(`/runs/${point.runId}`, '_blank');
                    }
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="index"
                  label={{ value: 'Index', position: 'insideBottom', offset: -5, style: { fontSize: 12 } }}
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  label={{ value: 'Value', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#f9fafb',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    fontSize: '12px',
                    padding: '8px 12px',
                  }}
                  formatter={(value: any, name: string, props: any) => {
                    return [value, 'Value'];
                  }}
                  labelFormatter={(value, payload) => {
                    if (payload && payload[0] && payload[0].payload) {
                      const point = payload[0].payload;
                      return `Run: ${point.runId}\nTime: ${point.time}`;
                    }
                    return value;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name={selectedKey}
                  stroke={COLORS[metricKeys.indexOf(selectedKey) % COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3, style: { cursor: 'pointer' } }}
                  activeDot={{ r: 5, style: { cursor: 'pointer' } }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )
        ) : (
          /* Pareto Scatter Chart */
          paretoMetrics.length < 2 ? (
            <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
              Select at least 2 metrics for Pareto analysis
            </div>
          ) : paretoChartData.all.length === 0 ? (
            <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
              No runs with complete data for selected metrics
            </div>
          ) : paretoMetrics.length === 3 ? (
            /* 3D Pareto Visualization */
            <div className="w-full h-[550px] rounded-lg overflow-hidden" style={{ background: 'linear-gradient(135deg, #fafafa 0%, #f3f4f6 100%)' }}>
              <style>{`
                #pareto-3d-plot .nsewdrag {
                  cursor: default !important;
                }
                #pareto-3d-plot .nsewdrag.cursor-crosshair {
                  cursor: default !important;
                }
              `}</style>
              <Suspense
                fallback={
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    <div className="text-center space-y-2">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mx-auto"></div>
                      <div>Loading 3D visualization...</div>
                    </div>
                  </div>
                }
              >
                <Plot
                  divId="pareto-3d-plot"
                  data={plotly3DData as any}
                  onInitialized={(figure, graphDiv) => {
                    graphDiv.on('plotly_click', (data: any) => {
                      if (data && data.points && data.points[0]) {
                        const point = data.points[0];
                        const runId = point.customdata?.[4];
                        if (runId) {
                          window.open(`/runs/${runId}`, '_blank');
                        }
                      }
                    });
                  }}
                  onUpdate={(figure, graphDiv) => {
                    graphDiv.removeAllListeners('plotly_click');
                    graphDiv.on('plotly_click', (data: any) => {
                      if (data && data.points && data.points[0]) {
                        const point = data.points[0];
                        const runId = point.customdata?.[4];
                        if (runId) {
                          window.open(`/runs/${runId}`, '_blank');
                        }
                      }
                    });
                  }}
                  layout={{
                    autosize: true,
                    transition: {
                      duration: 0,
                    },
                    scene: {
                      xaxis: {
                        title: {
                          text: `${paretoMetrics[0].key} (${paretoMetrics[0].direction})`,
                          font: { size: 12, color: '#374151', family: 'system-ui' },
                        },
                        gridcolor: '#e5e7eb',
                        gridwidth: 1,
                        showbackground: true,
                        backgroundcolor: '#fafafa',
                        tickfont: { size: 10, color: '#6b7280' },
                      },
                      yaxis: {
                        title: {
                          text: `${paretoMetrics[1].key} (${paretoMetrics[1].direction})`,
                          font: { size: 12, color: '#374151', family: 'system-ui' },
                        },
                        gridcolor: '#e5e7eb',
                        gridwidth: 1,
                        showbackground: true,
                        backgroundcolor: '#fafafa',
                        tickfont: { size: 10, color: '#6b7280' },
                      },
                      zaxis: {
                        title: {
                          text: `${paretoMetrics[2].key} (${paretoMetrics[2].direction})`,
                          font: { size: 12, color: '#374151', family: 'system-ui' },
                        },
                        gridcolor: '#e5e7eb',
                        gridwidth: 1,
                        showbackground: true,
                        backgroundcolor: '#fafafa',
                        tickfont: { size: 10, color: '#6b7280' },
                      },
                      camera: {
                        eye: { x: 1.7, y: 1.7, z: 1.3 },
                        center: { x: 0, y: 0, z: 0 },
                        up: { x: 0, y: 0, z: 1 },
                      },
                      aspectmode: 'cube',
                    },
                    showlegend: false,
                    hovermode: 'closest',
                    margin: {
                      l: 10,
                      r: 10,
                      t: 10,
                      b: 10,
                    },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    dragmode: 'orbit',
                  }}
                  config={{
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: ['toImage'],
                    modeBarButtonsToAdd: [],
                  }}
                  style={{ width: '100%', height: '100%' }}
                />
              </Suspense>
            </div>
          ) : (
            /* 2D Pareto Visualization */
            <div className="w-full h-[450px] rounded-lg overflow-hidden" style={{ background: 'linear-gradient(135deg, #fafafa 0%, #f3f4f6 100%)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  margin={{ top: 30, right: 30, bottom: 50, left: 70 }}
                >
                <defs>
                  <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur in="SourceAlpha" stdDeviation="2" />
                    <feOffset dx="0" dy="1" result="offsetblur" />
                    <feComponentTransfer>
                      <feFuncA type="linear" slope="0.2" />
                    </feComponentTransfer>
                    <feMerge>
                      <feMergeNode />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e5e7eb"
                  strokeOpacity={0.5}
                />
                <XAxis
                  type="number"
                  dataKey="x"
                  name={paretoMetrics[0].key}
                  label={{
                    value: `${paretoMetrics[0].key} (${paretoMetrics[0].direction})`,
                    position: 'bottom',
                    offset: 25,
                    style: {
                      fontSize: 13,
                      fontWeight: 600,
                      fill: '#374151'
                    },
                  }}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  domain={['dataMin - 0.05 * abs(dataMin)', 'dataMax + 0.05 * abs(dataMax)']}
                  stroke="#9ca3af"
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name={paretoMetrics[1].key}
                  label={{
                    value: `${paretoMetrics[1].key} (${paretoMetrics[1].direction})`,
                    angle: -90,
                    position: 'insideLeft',
                    offset: 10,
                    style: {
                      fontSize: 13,
                      fontWeight: 600,
                      fill: '#374151'
                    },
                  }}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  domain={['dataMin - 0.05 * abs(dataMin)', 'dataMax + 0.05 * abs(dataMax)']}
                  stroke="#9ca3af"
                />
                <Tooltip
                  cursor={{
                    strokeDasharray: '5 5',
                    stroke: '#94a3b8',
                    strokeWidth: 1
                  }}
                  contentStyle={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    padding: 0,
                  }}
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const data = payload[0].payload;
                    if (!data.runId) return null; // Skip line tooltips

                    const isPareto = data.isParetoOptimal;
                    const bgColor = isPareto ? '#f0fdf4' : '#fafafa';
                    const borderColor = isPareto ? '#86efac' : '#d1d5db';

                    return (
                      <div
                        style={{
                          backgroundColor: bgColor,
                          border: `1px solid ${borderColor}`,
                          borderRadius: '6px',
                          padding: '8px 12px',
                          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                          fontFamily: 'system-ui, -apple-system, sans-serif',
                          lineHeight: '1.4',
                        }}
                      >
                        <div style={{ fontWeight: 600, fontSize: '12px', color: '#1f2937' }}>
                          Run: {data.runId.slice(0, 8)}...
                        </div>
                        <div style={{ fontSize: '12px', color: '#374151' }}>
                          {paretoMetrics[0].key}: {data.x?.toFixed(4)}
                        </div>
                        <div style={{ fontSize: '12px', color: '#374151' }}>
                          {paretoMetrics[1].key}: {data.y?.toFixed(4)}
                        </div>
                      </div>
                    );
                  }}
                />
                {/* Line connecting Pareto optimal points */}
                {paretoChartData.paretoLine.length > 1 && (
                  <Line
                    type="monotone"
                    dataKey="y"
                    data={paretoChartData.paretoLine}
                    stroke={PARETO_COLOR}
                    strokeWidth={3}
                    dot={false}
                    isAnimationActive={false}
                    animationDuration={0}
                    connectNulls
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}
                {/* All scatter points */}
                <Scatter
                  name="Runs"
                  data={paretoChartData.all}
                  isAnimationActive={false}
                  onClick={(data: any) => {
                    if (data && data.runId) {
                      window.open(`/runs/${data.runId}`, '_blank');
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {paretoChartData.all.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.isParetoOptimal ? PARETO_COLOR : DOMINATED_COLOR}
                      fillOpacity={entry.isParetoOptimal ? 0.95 : 0.4}
                      r={entry.isParetoOptimal ? 7 : 5}
                      stroke={entry.isParetoOptimal ? '#059669' : '#6b7280'}
                      strokeWidth={entry.isParetoOptimal ? 2 : 1}
                      strokeOpacity={entry.isParetoOptimal ? 0.8 : 0.3}
                    />
                  ))}
                </Scatter>
              </ComposedChart>
            </ResponsiveContainer>
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
}
