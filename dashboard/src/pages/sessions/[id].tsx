import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Bot, TrendingUp, Clock, Zap, DollarSign, Brain, Wrench, User } from 'lucide-react';
import { formatDuration } from '../../lib/format';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Pagination } from '../../components/ui/pagination';
import { formatDistanceToNow } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts';
import type { Status, Run, Session, Span } from '../../types';
import { graphqlQuery } from '../../lib/graphql-client';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown' | 'info'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'info',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

const COMPLETIONS_PAGE_SIZE = 10;

interface SessionResponse {
  session: Session & {
    runs: Run[];
  };
}

interface RunWithSpans {
  run: Run;
  spans: Span[];
}

interface TimelineItem {
  type: 'user_input' | 'thinking' | 'text' | 'tool_use' | 'processing';
  name: string;
  duration?: number; // in seconds
  isError?: boolean;
  timestamp?: number; // milliseconds
  content?: string; // for thinking and text blocks
  input?: string; // for tool calls (JSON string)
  output?: string; // for tool calls (JSON string)
}

// Build timeline from actual spans with processing gaps
function buildTimelineFromSpans(spans: Span[], runDuration: number): TimelineItem[] {
  if (!spans || spans.length === 0) return [];

  // Sort spans by timestamp
  const sortedSpans = [...spans].sort((a, b) => {
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return timeA - timeB;
  });

  // Get user input from last span (end_turn span has the prompt)
  const firstSpan = sortedSpans[0];
  let userInput = '';
  // Search from last span backwards (prompt only stored in end_turn span)
  for (let i = sortedSpans.length - 1; i >= 0; i--) {
    const promptContent = sortedSpans[i].spanAttributes?.['gen_ai.prompt.0.content'];
    if (promptContent && promptContent.trim()) {
      userInput = promptContent;
      break;
    }
  }
  if (!userInput) {
    userInput = 'User input';
  }
  const runStartTimestamp = firstSpan?.timestamp ? new Date(firstSpan.timestamp).getTime() : 0;

  const operations: TimelineItem[] = [];

  // Convert each span to a timeline item
  for (const span of sortedSpans) {
    const attrs = span.spanAttributes || {};
    const timestamp = span.timestamp ? new Date(span.timestamp).getTime() : 0;
    const duration = span.duration ? span.duration / 1_000_000_000 : 0; // nanoseconds to seconds
    const semanticKind = span.semanticKind;

    // Get content based on semantic kind
    let content = '';
    let name = '';
    let type: TimelineItem['type'] = 'processing';

    if (semanticKind === 'processing') {
      // Processing gap (inference latency, waiting)
      operations.push({
        type: 'processing',
        name: 'Processing',
        duration,
        timestamp,
      });
      continue;
    } else if (semanticKind === 'thinking') {
      content = attrs['gen_ai.completion.0.content'] as string || '';
      name = 'Thinking';
      type = 'thinking';
    } else if (semanticKind === 'tool') {
      const toolName = attrs['tool.name'] as string || attrs['gen_ai.completion.0.tool_calls.0.name'] as string || 'Tool';
      name = toolName;
      type = 'tool_use';

      // Get tool input/output
      const toolInput = attrs['gen_ai.completion.0.tool_calls.0.arguments'] as string;
      const toolOutput = attrs['alphatrion.completion.0.tool_calls.0.output'] as string;
      const statusCode = attrs['alphatrion.completion.0.tool_calls.0.status_code'] as string;

      operations.push({
        type: 'tool_use',
        name,
        duration,
        timestamp,
        isError: statusCode === 'ERROR',
        input: toolInput,
        output: toolOutput
      });
      continue;
    } else if (semanticKind === 'text-generation') {
      content = attrs['gen_ai.completion.0.content'] as string || '';
      const preview = content.substring(0, 25) || 'Response';
      name = preview.trim() + '...';
      type = 'text';
    } else {
      // Skip unknown kinds
      continue;
    }

    operations.push({
      type,
      name,
      duration,
      timestamp,
      content
    });
  }

  // Now build the full timeline with user input
  const timeline: TimelineItem[] = [];

  // Add user input at the beginning
  // Duration = time from user input to first operation
  const firstOpTimestamp = operations[0]?.timestamp || runStartTimestamp;
  const userInputDuration = (firstOpTimestamp - runStartTimestamp) / 1000; // in seconds

  timeline.push({
    type: 'user_input',
    name: userInput.length > 30 ? userInput.substring(0, 30) + '...' : userInput,
    duration: userInputDuration, // Use actual duration (can be 0)
    timestamp: runStartTimestamp,
    content: userInput
  });

  // Add all operations (durations now include any processing/waiting time)
  timeline.push(...operations);

  return timeline;
}


export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');

  const [session, setSession] = useState<Session | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [runSpans, setRunSpans] = useState<RunWithSpans[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunIdx, setSelectedRunIdx] = useState<number | null>(null);
  const [selectedTimelineItemIdx, setSelectedTimelineItemIdx] = useState<number | null>(null);
  const [completionsPage, setCompletionsPage] = useState(0);

  useEffect(() => {
    if (!id) return;

    const fetchSession = async () => {
      try {
        const data = await graphqlQuery<SessionResponse>(
          `query GetSession($sessionId: ID!) {
            session(sessionId: $sessionId) {
              id
              agentId
              teamId
              userId
              meta
              createdAt
              updatedAt
              runs(page: 0, pageSize: 1000) {
                id
                teamId
                userId
                sessionId
                meta
                duration
                status
                createdAt
                aggregatedUsage {
                  totalTokens
                  inputTokens
                  outputTokens
                }
              }
            }
          }`,
          { sessionId: id }
        );
        setSession(data.session);
        const fetchedRuns = data.session?.runs || [];
        setRuns(fetchedRuns);

        // Fetch ALL spans for the session in one query
        try {
          const spanData = await graphqlQuery<{ spansBySessionId: Span[] }>(
            `query GetSessionSpans($sessionId: ID!) {
              spansBySessionId(sessionId: $sessionId) {
                timestamp
                traceId
                spanId
                parentSpanId
                spanName
                spanKind
                semanticKind
                duration
                statusCode
                statusMessage
                spanAttributes
                runId
              }
            }`,
            { sessionId: id }
          );

          // Group spans by runId
          const spansByRunId = new Map<string, Span[]>();
          for (const span of spanData.spansBySessionId || []) {
            const runId = span.runId || '';
            if (!spansByRunId.has(runId)) {
              spansByRunId.set(runId, []);
            }
            spansByRunId.get(runId)!.push(span);
          }

          // Combine runs with their spans
          const runsWithSpans: RunWithSpans[] = fetchedRuns.map(run => ({
            run,
            spans: spansByRunId.get(run.id) || []
          }));

          // Sort by run created time (newest first)
          runsWithSpans.sort((a, b) => new Date(b.run.createdAt).getTime() - new Date(a.run.createdAt).getTime());
          setRunSpans(runsWithSpans);
        } catch (err) {
          console.error('Failed to fetch spans for session:', err);
          setRunSpans(fetchedRuns.map(run => ({ run, spans: [] })));
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, [id]);


  // Compute aggregate metrics
  const metrics = useMemo(() => {
    const totalTokens = runs.reduce((sum, r) => sum + (r.aggregatedUsage?.totalTokens || 0), 0);
    const inputTokens = runs.reduce((sum, r) => sum + (r.aggregatedUsage?.inputTokens || 0), 0);
    const outputTokens = runs.reduce((sum, r) => sum + (r.aggregatedUsage?.outputTokens || 0), 0);
    const totalDuration = runs.reduce((sum, r) => sum + (r.duration || 0), 0);
    const avgDuration = runs.length > 0 ? totalDuration / runs.length : 0;
    const completedRuns = runs.filter(r => r.status === 'COMPLETED').length;
    const failedRuns = runs.filter(r => r.status === 'FAILED').length;
    const successRate = runs.length > 0 ? (completedRuns / runs.length) * 100 : 0;

    // Cost estimation (approximate: $3/M input tokens, $15/M output tokens for Claude)
    const estimatedCost = (inputTokens * 3 / 1_000_000) + (outputTokens * 15 / 1_000_000);

    return {
      totalTokens,
      inputTokens,
      outputTokens,
      totalDuration,
      avgDuration,
      completedRuns,
      failedRuns,
      successRate,
      estimatedCost,
    };
  }, [runs]);


  // Chart data: tokens over time
  const tokenChartData = useMemo(() => {
    return runs.map((run, idx) => ({
      index: idx + 1,
      name: `Run ${idx + 1}`,
      inputTokens: run.aggregatedUsage?.inputTokens || 0,
      outputTokens: run.aggregatedUsage?.outputTokens || 0,
      totalTokens: run.aggregatedUsage?.totalTokens || 0,
    }));
  }, [runs]);

  // Chart data: duration over time
  const durationChartData = useMemo(() => {
    return runs.map((run, idx) => ({
      index: idx + 1,
      name: `Run ${idx + 1}`,
      duration: run.duration || 0,
    }));
  }, [runs]);

  // Operation distribution by semantic kind
  const operationDistributionData = useMemo(() => {
    const countsByKind: Record<string, number> = {
      'text-generation': 0,
      'thinking': 0,
      'tool': 0,
    };

    // Count operations by semantic kind
    for (const runWithSpans of runSpans) {
      for (const span of runWithSpans.spans) {
        const kind = span.semanticKind;
        if (kind === 'text-generation' || kind === 'thinking' || kind === 'tool') {
          countsByKind[kind]++;
        }
      }
    }

    const colorMap: Record<string, string> = {
      'text-generation': '#10b981', // green
      'thinking': '#8b5cf6',        // purple
      'tool': '#3b82f6',            // blue
    };

    return Object.entries(countsByKind)
      .filter(([_, count]) => count > 0)
      .map(([kind, count]) => ({
        name: kind.charAt(0).toUpperCase() + kind.slice(1).replace('-', ' '),
        value: count,
        color: colorMap[kind] || '#6b7280',
      }))
      .sort((a, b) => b.value - a.value);
  }, [runSpans]);

  // Token distribution by semantic kind
  const tokenDistributionData = useMemo(() => {
    const tokensByKind: Record<string, { input: number; output: number; total: number }> = {
      'text-generation': { input: 0, output: 0, total: 0 },
      'thinking': { input: 0, output: 0, total: 0 },
      'tool': { input: 0, output: 0, total: 0 },
      'processing': { input: 0, output: 0, total: 0 },
    };

    // Aggregate tokens by semantic kind
    for (const runWithSpans of runSpans) {
      for (const span of runWithSpans.spans) {
        const kind = span.semanticKind;
        const attrs = span.spanAttributes || {};
        const inputTokens = parseInt(attrs['gen_ai.usage.input_tokens'] as string) || 0;
        const outputTokens = parseInt(attrs['gen_ai.usage.output_tokens'] as string) || 0;

        if (tokensByKind[kind]) {
          tokensByKind[kind].input += inputTokens;
          tokensByKind[kind].output += outputTokens;
          tokensByKind[kind].total += inputTokens + outputTokens;
        }
      }
    }

    const colorMap: Record<string, string> = {
      'text-generation': '#10b981', // green
      'thinking': '#8b5cf6',        // purple
      'tool': '#3b82f6',            // blue
      'processing': '#6b7280',      // gray
    };

    return Object.entries(tokensByKind)
      .filter(([_, tokens]) => tokens.total > 0)
      .map(([kind, tokens]) => ({
        name: kind.charAt(0).toUpperCase() + kind.slice(1).replace('-', ' '),
        inputTokens: tokens.input,
        outputTokens: tokens.output,
        totalTokens: tokens.total,
        color: colorMap[kind] || '#6b7280',
      }))
      .sort((a, b) => b.totalTokens - a.totalTokens);
  }, [runSpans]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Bot className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Session not found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {error || 'The requested session could not be found.'}
            </p>
            <Button onClick={() => navigate('/agents')}>
              Back to Agents
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground font-mono">
            {session.agentId}
          </h1>
          <p className="mt-0.5 text-muted-foreground font-mono text-xs">
            {session.id}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="runs">Completions</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Completions
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{runs.length}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {metrics.completedRuns} completed / {metrics.failedRuns} failed
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Tokens
                </CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.totalTokens.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {metrics.inputTokens.toLocaleString()} in / {metrics.outputTokens.toLocaleString()} out
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Avg Duration
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatDuration(metrics.avgDuration)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Total: {formatDuration(metrics.totalDuration)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Est. Cost
                </CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${metrics.estimatedCost.toFixed(4)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Success rate: {metrics.successRate.toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Token Usage Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Token Usage per Completion</CardTitle>
                <CardDescription className="text-xs">Input vs Output tokens</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={tokenChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="index" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ fontSize: '12px', backgroundColor: '#fafafa', border: '1px solid #d1d5db' }}
                    />
                    <Bar dataKey="inputTokens" stackId="a" fill="#0ea5e9" name="Input" />
                    <Bar dataKey="outputTokens" stackId="a" fill="#8b5cf6" name="Output" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Duration Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Response Time</CardTitle>
                <CardDescription className="text-xs">Duration per completion</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={durationChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="index" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ fontSize: '12px', backgroundColor: '#fafafa', border: '1px solid #d1d5db' }}
                      formatter={(value: number) => formatDuration(value)}
                    />
                    <Line type="monotone" dataKey="duration" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Operation Distribution Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Operation Distribution</CardTitle>
                <CardDescription className="text-xs">By operation type</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={operationDistributionData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      style={{ fontSize: '12px' }}
                    >
                      {operationDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ fontSize: '12px', backgroundColor: '#fafafa', border: '1px solid #d1d5db' }}
                      formatter={(value: number) => `${value} operations`}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '12px' }}
                      iconType="circle"
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Token Distribution by Operation Type */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Token Distribution by Operation</CardTitle>
                <CardDescription className="text-xs">Input vs Output tokens</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={tokenDistributionData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                    <Tooltip
                      contentStyle={{ fontSize: '12px', backgroundColor: '#fafafa', border: '1px solid #d1d5db' }}
                      formatter={(value: number) => value.toLocaleString()}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '12px' }}
                      iconType="circle"
                    />
                    <Bar dataKey="inputTokens" stackId="a" fill="#0ea5e9" name="Input" />
                    <Bar dataKey="outputTokens" stackId="a" fill="#8b5cf6" name="Output" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Completions Tab */}
        <TabsContent value="runs" className="space-y-2">
          {runSpans.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center h-64 text-center p-6">
                <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                  <Bot className="h-6 w-6 text-muted-foreground/60" />
                </div>
                <p className="text-xs font-medium text-foreground mb-1">No completions yet</p>
                <p className="text-[10px] text-muted-foreground max-w-xs">
                  {runs.length > 0
                    ? 'Trace data may not be available for this session'
                    : 'Completions will appear here as you interact with the agent'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="space-y-2">
                {runSpans.slice(completionsPage * COMPLETIONS_PAGE_SIZE, (completionsPage + 1) * COMPLETIONS_PAGE_SIZE).map((runWithSpans, idx) => {
                  const actualIdx = completionsPage * COMPLETIONS_PAGE_SIZE + idx;
                  const isExpanded = selectedRunIdx === actualIdx;

                  // Extract user input from spans
                  // Sort spans by timestamp to get the first one
                  const sortedSpans = [...runWithSpans.spans].sort((a, b) => {
                    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                    return timeA - timeB;
                  });

                  // Try to find user input from the first span with content (skip processing spans)
                  let userInput = '';
                  for (const span of sortedSpans) {
                    const attrs = span.spanAttributes || {};

                    // Try different attribute paths in order of likelihood
                    const promptContent = attrs['gen_ai.prompt.0.content'] as string;

                    if (promptContent && promptContent.trim()) {
                      userInput = promptContent;
                      break;
                    }

                    // Fallback to other possible locations
                    if (!userInput) {
                      userInput = attrs['llm.prompts.0.content'] as string ||
                        attrs['input.value'] as string ||
                        attrs['input'] as string || '';
                    }

                    if (userInput && userInput.trim()) break;
                  }

                  const displayInput = userInput.length > 100 ? userInput.substring(0, 100) + '...' : userInput;

                  return (
                    <Card
                      key={runWithSpans.run.id}
                      className={`cursor-pointer transition-all hover:shadow-md ${isExpanded ? 'ring-2 ring-primary' : ''
                        }`}
                      onClick={() => {
                        setSelectedRunIdx(isExpanded ? null : actualIdx);
                        setSelectedTimelineItemIdx(null); // Reset timeline item selection
                      }}
                    >
                      <CardContent className="p-3">
                        {/* Completion Header */}
                        <div className="flex items-start gap-2">
                          <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-1.5 ${runWithSpans.run.status === 'COMPLETED' ? 'bg-green-500' :
                              runWithSpans.run.status === 'FAILED' ? 'bg-red-500' :
                                'bg-yellow-500'
                            }`} />
                          <div className="flex-1 min-w-0">
                            {/* User Input */}
                            <div className="flex items-start gap-2 mb-1">
                              {userInput ? (
                                <p className="text-sm text-foreground line-clamp-2 flex-1">
                                  {displayInput}
                                </p>
                              ) : (
                                <p className="text-sm text-muted-foreground italic flex-1">
                                  [No user input]
                                </p>
                              )}
                              <Badge variant={STATUS_VARIANTS[runWithSpans.run.status]} className="text-[10px] flex-shrink-0">
                                {runWithSpans.run.status}
                              </Badge>
                            </div>

                            {/* Metadata */}
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                              <span>{formatDistanceToNow(new Date(runWithSpans.run.createdAt), { addSuffix: true })}</span>
                              {runWithSpans.run.duration && (
                                <>
                                  <span>•</span>
                                  <Clock className="h-3 w-3" />
                                  <span className="font-mono">{formatDuration(runWithSpans.run.duration)}</span>
                                </>
                              )}
                              {runWithSpans.run.aggregatedUsage && runWithSpans.run.aggregatedUsage.totalTokens > 0 && (
                                <>
                                  <span>•</span>
                                  <Zap className="h-3 w-3" />
                                  <span className="font-mono">{runWithSpans.run.aggregatedUsage.totalTokens.toLocaleString()} tokens</span>
                                </>
                              )}
                              {runWithSpans.spans.length > 0 && (
                                <>
                                  <span>•</span>
                                  <span>{runWithSpans.spans.length} span{runWithSpans.spans.length !== 1 ? 's' : ''}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Expanded Content */}
                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t space-y-3">

                            {/* Timeline */}
                            <div>
                              {(() => {
                                // Build timeline from all spans
                                const timeline = buildTimelineFromSpans(runWithSpans.spans, runWithSpans.run.duration || 0);

                                if (timeline.length === 0) {
                                  return (
                                    <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
                                      No timeline data available
                                    </div>
                                  );
                                }

                                // Get actual time range from timeline items
                                const timestamps = timeline.filter(t => t.timestamp && t.timestamp > 0).map(t => t.timestamp!);
                                const minTimestamp = Math.min(...timestamps);
                                const maxTimestamp = Math.max(...timestamps);

                                // Calculate actual duration based on timestamps, with padding for last operation
                                const lastItem = timeline[timeline.length - 1];
                                const lastItemEnd = lastItem.timestamp && lastItem.duration
                                  ? lastItem.timestamp + (lastItem.duration * 1000)
                                  : maxTimestamp;
                                const totalDurationMs = Math.max(lastItemEnd - minTimestamp, 1000); // At least 1 second

                                return (
                                  <>
                                    {/* Timeline Header */}
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="flex items-center gap-2">
                                        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Timeline</h4>
                                        <span className="text-[10px] text-muted-foreground font-mono">
                                          {timeline.length - 1} operations • {formatDuration(totalDurationMs / 1000)}
                                        </span>
                                      </div>
                                      {runWithSpans.run.aggregatedUsage && (
                                        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                                          <Zap className="h-3 w-3" />
                                          {runWithSpans.run.aggregatedUsage.inputTokens}↓ {runWithSpans.run.aggregatedUsage.outputTokens}↑
                                        </div>
                                      )}
                                    </div>

                                    {/* Timeline Table */}
                                    <div className="border rounded overflow-hidden">
                                      {/* Column Headers */}
                                      <div className="flex items-center bg-muted/30 border-b text-[9px] text-muted-foreground uppercase tracking-wide h-6">
                                        <div className="flex-shrink-0 flex items-center h-full" style={{ width: '140px', paddingLeft: '6px' }}>
                                          Operation
                                        </div>
                                        <div className="flex-shrink-0 flex items-center h-full" style={{ width: '70px', paddingLeft: '6px' }}>
                                          Duration
                                        </div>
                                        <div className="flex-1 flex items-center h-full" style={{ paddingLeft: '6px', paddingRight: '6px' }}>
                                          Timeline
                                        </div>
                                      </div>

                                      {/* Timeline Rows */}
                                      {timeline.map((item, idx) => {
                                        const hasActualDuration = item.duration !== undefined && item.duration > 0;
                                        const displayDuration = item.duration || 0;

                                        // Position: bar STARTS at timestamp and extends for duration
                                        const itemTimestamp = item.timestamp || minTimestamp;
                                        const startOffsetMs = itemTimestamp - minTimestamp;
                                        const leftPercent = (startOffsetMs / totalDurationMs) * 100;

                                        // Bar width: how long the operation takes
                                        const durationMs = displayDuration * 1000;
                                        const widthPercent = (durationMs / totalDurationMs) * 100;

                                        let badgeColor = '';
                                        let barColor = '';
                                        let icon = null;
                                        let typeLabel = '';

                                        if (item.type === 'user_input') {
                                          badgeColor = 'bg-green-100 text-green-700 border-green-200';
                                          barColor = 'bg-green-500';
                                          icon = <User className="h-3 w-3" />;
                                          typeLabel = 'User';
                                        } else if (item.type === 'thinking') {
                                          badgeColor = 'bg-purple-100 text-purple-700 border-purple-200';
                                          barColor = 'bg-purple-500';
                                          icon = <Brain className="h-3 w-3" />;
                                          typeLabel = 'Think';
                                        } else if (item.type === 'text') {
                                          badgeColor = 'bg-gray-100 text-gray-700 border-gray-200';
                                          barColor = 'bg-gray-500';
                                          icon = <Bot className="h-3 w-3" />;
                                          typeLabel = 'Text';
                                        } else if (item.type === 'tool_use') {
                                          if (item.isError) {
                                            badgeColor = 'bg-red-100 text-red-700 border-red-200';
                                            barColor = 'bg-red-500';
                                          } else {
                                            badgeColor = 'bg-blue-100 text-blue-700 border-blue-200';
                                            barColor = 'bg-blue-500';
                                          }
                                          icon = <Wrench className="h-3 w-3" />;
                                          typeLabel = 'Tool';
                                        } else if (item.type === 'processing') {
                                          badgeColor = 'bg-slate-100 text-slate-600 border-slate-200';
                                          barColor = 'bg-slate-400';
                                          icon = <Clock className="h-3 w-3" />;
                                          typeLabel = 'Proc';
                                        }

                                        return (
                                          <div key={idx}>
                                            <div
                                              className={`flex items-center border-b border-border hover:bg-muted/20 transition-colors h-8 cursor-pointer ${selectedTimelineItemIdx === idx ? 'bg-accent' : ''
                                                }`}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setSelectedTimelineItemIdx(selectedTimelineItemIdx === idx ? null : idx);
                                              }}
                                            >
                                              {/* Operation Name */}
                                              <div className="flex-shrink-0 flex items-center gap-1 h-full min-w-0" style={{ width: '140px', paddingLeft: '6px', paddingRight: '6px' }}>
                                                <Badge variant="outline" className={`${badgeColor} flex items-center gap-0.5 px-1 py-0 text-[9px] font-medium flex-shrink-0 h-4`}>
                                                  {icon}
                                                  <span>{typeLabel}</span>
                                                </Badge>
                                                <span className="text-[11px] truncate text-foreground" title={item.name}>
                                                  {item.name}
                                                </span>
                                              </div>

                                              {/* Duration */}
                                              <div className="flex-shrink-0 flex items-center gap-1 text-foreground h-full" style={{ width: '70px', paddingLeft: '6px' }}>
                                                <span className={`text-[10px] font-mono ${hasActualDuration ? '' : 'text-muted-foreground italic'}`}>
                                                  {hasActualDuration ? formatDuration(displayDuration) : <span className="text-muted-foreground/40">~0ms</span>}
                                                </span>
                                              </div>

                                              {/* Timeline Bar */}
                                              <div className="flex-1 relative h-full min-w-0 flex items-center" style={{ paddingLeft: '6px', paddingRight: '6px' }}>
                                                {hasActualDuration && (
                                                  <div
                                                    className={`${barColor} absolute h-4 rounded flex items-center px-1 text-white text-[9px] font-medium`}
                                                    style={{
                                                      left: `${Math.max(0, Math.min(99, leftPercent))}%`,
                                                      width: `${Math.max(1, Math.min(100 - leftPercent, widthPercent))}%`,
                                                    }}
                                                    title={`${item.name}\nStart: +${(startOffsetMs / 1000).toFixed(2)}s\nDuration: ${formatDuration(displayDuration)}`}
                                                  >
                                                    <span className="truncate">{formatDuration(displayDuration)}</span>
                                                  </div>
                                                )}
                                              </div>
                                            </div>

                                            {/* Details Panel */}
                                            {selectedTimelineItemIdx === idx && item.type !== 'processing' && (
                                              <div className="border-b border-border bg-muted/10 p-3">
                                                {item.type === 'user_input' && item.content && (
                                                  <div>
                                                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">User Input</h5>
                                                    <div className="bg-background rounded border p-2.5">
                                                      <pre className="text-xs text-foreground whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                                                        {item.content}
                                                      </pre>
                                                    </div>
                                                  </div>
                                                )}

                                                {item.type === 'thinking' && item.content && (
                                                  <div>
                                                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Thinking</h5>
                                                    <div className="bg-background rounded border p-2.5">
                                                      <pre className="text-xs text-foreground font-mono whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                                                        {item.content}
                                                      </pre>
                                                    </div>
                                                  </div>
                                                )}

                                                {item.type === 'text' && item.content && (
                                                  <div>
                                                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Response</h5>
                                                    <div className="bg-background rounded border p-2.5">
                                                      <pre className="text-xs text-foreground whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                                                        {item.content}
                                                      </pre>
                                                    </div>
                                                  </div>
                                                )}

                                                {item.type === 'tool_use' && (
                                                  <div className="space-y-3">
                                                    {item.input && (
                                                      <div>
                                                        <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Input</h5>
                                                        <div className="bg-background rounded border p-2.5">
                                                          <pre className="text-xs text-foreground font-mono whitespace-pre-wrap break-words max-h-64 overflow-y-auto">
                                                            {(() => {
                                                              try {
                                                                return JSON.stringify(JSON.parse(item.input), null, 2);
                                                              } catch {
                                                                return item.input;
                                                              }
                                                            })()}
                                                          </pre>
                                                        </div>
                                                      </div>
                                                    )}

                                                    {item.output && (
                                                      <div>
                                                        <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Output</h5>
                                                        <div className="bg-background rounded border p-2.5">
                                                          <pre className="text-xs text-foreground font-mono whitespace-pre-wrap break-words max-h-64 overflow-y-auto">
                                                            {item.output}
                                                          </pre>
                                                        </div>
                                                      </div>
                                                    )}

                                                    {item.isError && (
                                                      <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded p-2">
                                                        <p className="text-xs text-red-700 dark:text-red-300 font-semibold">
                                                          Tool execution failed
                                                        </p>
                                                      </div>
                                                    )}
                                                  </div>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </>
                                );
                              })()}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {/* Pagination */}
              <Pagination
                currentPage={completionsPage}
                totalPages={Math.max(1, Math.ceil(runSpans.length / COMPLETIONS_PAGE_SIZE))}
                pageSize={COMPLETIONS_PAGE_SIZE}
                totalItems={runSpans.length}
                onPageChange={setCompletionsPage}
                itemName="completions"
              />
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
