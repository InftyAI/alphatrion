import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Clock, Zap, Database, Globe, Bot, X, Route } from 'lucide-react';
import type { Span } from '../../types';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

interface TraceTimelineProps {
  spans: Span[];
}

interface SpanNode {
  span: Span;
  children: SpanNode[];
  depth: number;
  totalTokens?: number;
  inputTokens?: number;
  outputTokens?: number;
}

// Status color mapping
// Note: UNSET is the default OpenTelemetry status (not an error)
const STATUS_COLORS: Record<string, string> = {
  'OK': 'bg-green-500',
  'ERROR': 'bg-red-500',
  'UNSET': 'bg-green-500', // Treat UNSET as successful (default behavior)
};

// Span type detection and styling
const getSpanType = (span: Span): { label: string; icon: JSX.Element; badgeColor: string } => {
  const name = span.spanName.toLowerCase();
  const kind = span.spanKind;

  if (name.includes('openai') || name.includes('chat') || name.includes('completion')) {
    return { label: 'LLM', icon: <Bot className="h-3 w-3" />, badgeColor: 'bg-purple-100 text-purple-700 border-purple-200' };
  }
  if (kind === 'CLIENT' || name.includes('http') || name.includes('api')) {
    return { label: 'API', icon: <Globe className="h-3 w-3" />, badgeColor: 'bg-blue-100 text-blue-700 border-blue-200' };
  }
  if (name.includes('db') || name.includes('database') || name.includes('query')) {
    return { label: 'DB', icon: <Database className="h-3 w-3" />, badgeColor: 'bg-cyan-100 text-cyan-700 border-cyan-200' };
  }
  if (span.spanAttributes?.['traceloop.span.kind'] === 'workflow') {
    return { label: 'Workflow', icon: <Route className="h-3 w-3" />, badgeColor: 'bg-indigo-100 text-indigo-700 border-indigo-200' };
  }
  if (span.spanAttributes?.['traceloop.span.kind'] === 'task') {
    return { label: 'Task', icon: <Zap className="h-3 w-3" />, badgeColor: 'bg-amber-100 text-amber-700 border-amber-200' };
  }

  return { label: 'Span', icon: <Clock className="h-3 w-3" />, badgeColor: 'bg-gray-100 text-gray-700 border-gray-200' };
};

export function TraceTimeline({ spans }: TraceTimelineProps) {
  // Initialize with root spans expanded
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(() => {
    return new Set(spans.filter(s => !s.parentSpanId || s.parentSpanId === '').map(s => s.spanId));
  });
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);

  const expandAll = () => {
    const allSpanIds = new Set(spans.map(s => s.spanId));
    setExpandedSpans(allSpanIds);
  };

  const collapseAll = () => {
    setExpandedSpans(new Set());
  };

  // Build hierarchical tree structure
  const spanTree = useMemo(() => {
    if (!spans || spans.length === 0) return [];

    // Create a map for quick lookup
    const spanMap = new Map<string, SpanNode>();
    const rootSpans: SpanNode[] = [];

    // First pass: create all nodes
    spans.forEach(span => {
      spanMap.set(span.spanId, {
        span,
        children: [],
        depth: 0,
      });
    });

    // Second pass: build tree structure
    spans.forEach(span => {
      const node = spanMap.get(span.spanId)!;

      if (!span.parentSpanId || span.parentSpanId === '') {
        // Root span
        rootSpans.push(node);
      } else {
        // Child span
        const parent = spanMap.get(span.parentSpanId);
        if (parent) {
          node.depth = parent.depth + 1;
          parent.children.push(node);
        } else {
          // Parent not found, treat as root
          rootSpans.push(node);
        }
      }
    });

    // Sort children by timestamp
    const sortChildren = (nodes: SpanNode[]) => {
      nodes.sort((a, b) =>
        new Date(a.span.timestamp).getTime() - new Date(b.span.timestamp).getTime()
      );
      nodes.forEach(node => sortChildren(node.children));
    };

    // Aggregate tokens bottom-up (like Langfuse does for costs)
    const aggregateTokens = (node: SpanNode): void => {
      // First aggregate children
      node.children.forEach(child => aggregateTokens(child));

      // Get own tokens
      const ownInputTokens = parseInt(node.span.spanAttributes?.['gen_ai.usage.input_tokens'] as string) || 0;
      const ownOutputTokens = parseInt(node.span.spanAttributes?.['gen_ai.usage.output_tokens'] as string) || 0;
      const ownTotalTokens = parseInt(node.span.spanAttributes?.['llm.usage.total_tokens'] as string) || 0;

      // Sum children tokens
      const childInputTokens = node.children.reduce((sum, child) => sum + (child.inputTokens || 0), 0);
      const childOutputTokens = node.children.reduce((sum, child) => sum + (child.outputTokens || 0), 0);
      const childTotalTokens = node.children.reduce((sum, child) => sum + (child.totalTokens || 0), 0);

      // Aggregate
      node.inputTokens = ownInputTokens + childInputTokens;
      node.outputTokens = ownOutputTokens + childOutputTokens;
      node.totalTokens = ownTotalTokens + childTotalTokens;
    };

    sortChildren(rootSpans);
    rootSpans.forEach(node => aggregateTokens(node));
    return rootSpans;
  }, [spans]);

  // Calculate timeline dimensions
  const { minTimestamp, maxTimestamp, totalDuration } = useMemo(() => {
    if (!spans || spans.length === 0) {
      return { minTimestamp: 0, maxTimestamp: 0, totalDuration: 0 };
    }

    // Find earliest start time and latest end time
    const startTimes = spans.map(s => new Date(s.timestamp).getTime());
    const endTimes = spans.map(s => new Date(s.timestamp).getTime() + (s.duration / 1_000_000));

    const min = Math.min(...startTimes);
    const max = Math.max(...endTimes);
    const duration = max - min;

    return {
      minTimestamp: min,
      maxTimestamp: max,
      totalDuration: duration || 1, // Avoid division by zero
    };
  }, [spans]);

  const toggleSpan = (spanId: string) => {
    setExpandedSpans(prev => {
      const next = new Set(prev);
      if (next.has(spanId)) {
        next.delete(spanId);
      } else {
        next.add(spanId);
      }
      return next;
    });
  };

  const formatDuration = (nanoseconds: number) => {
    const microseconds = nanoseconds / 1000;
    const milliseconds = microseconds / 1000;
    const seconds = milliseconds / 1000;

    if (seconds >= 1) {
      return `${seconds.toFixed(2)}s`;
    } else if (milliseconds >= 1) {
      return `${milliseconds.toFixed(2)}ms`;
    } else {
      return `${microseconds.toFixed(2)}μs`;
    }
  };

  const renderSpanBar = (node: SpanNode) => {
    const { span } = node;
    const spanStart = new Date(span.timestamp).getTime();
    const spanEnd = spanStart + (span.duration / 1_000_000); // Convert ns to ms

    // Calculate position and width as percentages
    const leftPercent = ((spanStart - minTimestamp) / totalDuration) * 100;
    const widthPercent = ((spanEnd - spanStart) / totalDuration) * 100;

    const statusColor = STATUS_COLORS[span.statusCode] || STATUS_COLORS['UNSET'];

    return (
      <div
        className={`${statusColor} absolute h-6 rounded flex items-center px-1.5 text-white text-[10px] font-medium overflow-hidden transition-all hover:opacity-90 hover:shadow-md cursor-pointer shadow`}
        style={{
          left: `${leftPercent}%`,
          width: `${Math.max(widthPercent, 0.8)}%`, // Minimum width for visibility
        }}
        title={`${span.spanName}\nDuration: ${formatDuration(span.duration)}\nStatus: ${span.statusCode}\nKind: ${span.spanKind}`}
      >
        <span className="truncate">{formatDuration(span.duration)}</span>
      </div>
    );
  };

  const renderSpanNode = (node: SpanNode): JSX.Element => {
    const { span, children, depth, totalTokens, inputTokens, outputTokens } = node;
    const hasChildren = children.length > 0;
    const isExpanded = expandedSpans.has(span.spanId);
    const spanType = getSpanType(span);

    // Show aggregated tokens if has children, otherwise own tokens
    const isAggregated = hasChildren && totalTokens && totalTokens > 0;

    return (
      <div key={span.spanId}>
        {/* Span Row */}
        <div
          className={`flex items-center border-b border-border hover:bg-muted/30 transition-colors cursor-pointer h-10 ${
            selectedSpan?.spanId === span.spanId ? 'bg-accent' : ''
          }`}
          onClick={(e) => {
            // Don't trigger if clicking expand button
            if ((e.target as HTMLElement).closest('button')) return;
            setSelectedSpan(span);
          }}
        >
          {/* Left: Span info with expand button */}
          <div
            className="flex-shrink-0 flex items-center gap-1.5 h-full min-w-0"
            style={{ width: '320px', paddingLeft: `${depth * 10 + 8}px`, paddingRight: '8px' }}
          >
            {/* Tree connector line */}
            {depth > 0 && (
              <div className="absolute h-full border-l border-border/60" style={{ left: `${(depth - 1) * 10 + 8}px` }} />
            )}

            {/* Expand/collapse button */}
            {hasChildren ? (
              <button
                onClick={() => toggleSpan(span.spanId)}
                className="p-0.5 hover:bg-accent rounded flex-shrink-0 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                )}
              </button>
            ) : (
              <div className="w-[18px] flex-shrink-0" />
            )}

            {/* Type badge */}
            <Badge variant="outline" className={`${spanType.badgeColor} flex items-center gap-0.5 px-1.5 py-0.5 text-[11px] font-medium flex-shrink-0`}>
              {spanType.icon}
              <span>{spanType.label}</span>
            </Badge>

            {/* Span name */}
            <span className="text-[13px] font-medium truncate text-foreground" title={span.spanName}>
              {span.spanName}
            </span>
          </div>

          {/* Middle: Duration */}
          <div className="flex-shrink-0 flex items-center gap-1 whitespace-nowrap text-foreground h-full" style={{ width: '90px', paddingLeft: '8px', paddingRight: '8px' }}>
            <Clock className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
            <span className="text-[11px] font-mono">{formatDuration(span.duration)}</span>
          </div>

          {/* Middle: Tokens */}
          <div className="flex-shrink-0 flex items-center whitespace-nowrap text-foreground h-full" style={{ width: '90px', paddingLeft: '8px', paddingRight: '4px' }}>
            {totalTokens && totalTokens > 0 ? (
              <div className="flex flex-col justify-center">
                <div className="font-mono flex items-center text-[11px] leading-tight">
                  {isAggregated && <span className="inline-block align-middle mr-0.5 text-muted-foreground text-[10px]">∑</span>}
                  <span>{totalTokens.toLocaleString()}</span>
                </div>
                {inputTokens && outputTokens && inputTokens > 0 && outputTokens > 0 && (
                  <div className="text-muted-foreground text-[9px] font-mono leading-tight mt-0.5">
                    {inputTokens.toLocaleString()}↓ {outputTokens.toLocaleString()}↑
                  </div>
                )}
              </div>
            ) : (
              <span className="text-muted-foreground/40 text-[11px]">—</span>
            )}
          </div>

          {/* Right: Timeline bar */}
          <div className="flex-1 relative h-full min-w-0 flex items-center" style={{ paddingLeft: '2px', paddingRight: '8px' }}>
            {renderSpanBar(node)}
          </div>
        </div>

        {/* Children (if expanded) */}
        {hasChildren && isExpanded && (
          <div>{children.map(child => renderSpanNode(child))}</div>
        )}
      </div>
    );
  };

  if (!spans || spans.length === 0) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            No traces available
          </div>
        </CardContent>
      </Card>
    );
  }

  const renderSpanDetails = (span: Span) => {
    const spanType = getSpanType(span);
    const attrs = span.spanAttributes || {};

    // Extract model parameters
    const model = attrs['gen_ai.request.model'] || attrs['gen_ai.response.model'];
    const temperature = attrs['gen_ai.request.temperature'];
    const maxTokens = attrs['gen_ai.request.max_tokens'];
    const topP = attrs['gen_ai.request.top_p'];

    // Extract prompts
    const prompts: Array<{ role: string; content: string }> = [];
    let i = 0;
    while (attrs[`gen_ai.prompt.${i}.role`]) {
      prompts.push({
        role: attrs[`gen_ai.prompt.${i}.role`] as string,
        content: attrs[`gen_ai.prompt.${i}.content`] as string,
      });
      i++;
    }

    // Extract completions
    const completions: Array<{ role: string; content: string; finishReason?: string }> = [];
    i = 0;
    while (attrs[`gen_ai.completion.${i}.role`]) {
      completions.push({
        role: attrs[`gen_ai.completion.${i}.role`] as string,
        content: attrs[`gen_ai.completion.${i}.content`] as string,
        finishReason: attrs[`gen_ai.completion.${i}.finish_reason`] as string,
      });
      i++;
    }

    return (
      <Card className="mt-2 border-2">
        <CardContent className="p-3">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <Badge variant="outline" className={`${spanType.badgeColor} flex items-center gap-0.5 px-1.5 py-0.5 text-[11px]`}>
                {spanType.icon}
                {spanType.label}
              </Badge>
              <h4 className="font-semibold text-[13px]">{span.spanName}</h4>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedSpan(null)}
              className="h-6 w-6 p-0 hover:bg-muted"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>

          {/* Model Parameters */}
          {model && (
            <div className="mb-3">
              <h5 className="text-[11px] font-semibold mb-1.5 text-foreground uppercase tracking-wide">Model Configuration</h5>
              <div className="grid grid-cols-2 gap-1.5 text-[10px] border rounded-md p-2 bg-muted/30">
                <div className="col-span-2">
                  <span className="text-muted-foreground font-medium">Model:</span>
                  <span className="ml-1.5 font-mono text-foreground">{model}</span>
                </div>
                {temperature !== undefined && (
                  <div>
                    <span className="text-muted-foreground font-medium">Temperature:</span>
                    <span className="ml-1.5 font-mono text-foreground">{temperature}</span>
                  </div>
                )}
                {maxTokens && (
                  <div>
                    <span className="text-muted-foreground font-medium">Max Tokens:</span>
                    <span className="ml-1.5 font-mono text-foreground">{maxTokens}</span>
                  </div>
                )}
                {topP !== undefined && (
                  <div>
                    <span className="text-muted-foreground font-medium">Top P:</span>
                    <span className="ml-1.5 font-mono text-foreground">{topP}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Prompts */}
          {prompts.length > 0 && (
            <div className="mb-3">
              <h5 className="text-[11px] font-semibold mb-1.5 text-foreground uppercase tracking-wide">Input</h5>
              <div className="space-y-1.5">
                {prompts.map((prompt, idx) => (
                  <div key={idx} className="border rounded-md p-2 bg-muted/30">
                    <div className="text-[10px] font-semibold text-muted-foreground mb-1 uppercase tracking-wide">
                      {prompt.role}
                    </div>
                    <div className="text-[11px] whitespace-pre-wrap leading-relaxed text-foreground">{prompt.content}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completions */}
          {completions.length > 0 && (
            <div className="mb-3">
              <h5 className="text-[11px] font-semibold mb-1.5 text-foreground uppercase tracking-wide">Output</h5>
              <div className="space-y-1.5">
                {completions.map((completion, idx) => (
                  <div key={idx} className="border rounded-md p-2 bg-muted/30">
                    <div className="text-[10px] font-semibold text-muted-foreground mb-1 uppercase tracking-wide">
                      {completion.role}
                    </div>
                    <div className="text-[11px] whitespace-pre-wrap leading-relaxed text-foreground">{completion.content}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Show all attributes (collapsible) */}
          <details className="mt-2">
            <summary className="text-[11px] font-semibold cursor-pointer hover:text-foreground text-muted-foreground py-0.5 uppercase tracking-wide">
              All Attributes ({Object.keys(attrs).length})
            </summary>
            <div className="mt-1.5 text-[11px] space-y-0.5 bg-muted/30 rounded-md p-2 max-h-48 overflow-auto border">
              {Object.entries(attrs).map(([key, value]) => (
                <div key={key} className="grid grid-cols-3 gap-2 py-0.5">
                  <span className="text-muted-foreground truncate font-medium text-[10px]" title={key}>{key}:</span>
                  <span className="col-span-2 font-mono break-all text-[10px] text-foreground">{String(value)}</span>
                </div>
              ))}
            </div>
          </details>
        </CardContent>
      </Card>
    );
  };

  return (
    <Card className="shadow-sm">
      <CardContent className="p-3">
        {/* Header */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">Timeline</h3>
            <span className="text-[11px] text-muted-foreground">
              {formatDuration(totalDuration * 1_000_000)} · {spans.length} span{spans.length !== 1 ? 's' : ''}
            </span>

            {/* Expand/Collapse controls */}
            <div className="flex items-center gap-1 ml-2">
              <button
                onClick={expandAll}
                className="text-[11px] px-1.5 py-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              >
                Expand all
              </button>
              <span className="text-muted-foreground/30 text-xs">|</span>
              <button
                onClick={collapseAll}
                className="text-[11px] px-1.5 py-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              >
                Collapse all
              </button>
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-2 text-[11px]">
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span className="text-muted-foreground">Success</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
              <span className="text-muted-foreground">Error</span>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="border rounded-md overflow-hidden bg-background shadow-sm">
          {/* Column headers */}
          <div className="flex items-center bg-muted/50 border-b border-border font-semibold text-[10px] text-foreground uppercase tracking-wide h-8">
            <div className="flex-shrink-0 flex items-center h-full" style={{ width: '320px', paddingLeft: '8px', paddingRight: '8px' }}>
              Span Name
            </div>
            <div className="flex-shrink-0 flex items-center h-full" style={{ width: '90px', paddingLeft: '8px', paddingRight: '8px' }}>
              Duration
            </div>
            <div className="flex-shrink-0 flex items-center h-full" style={{ width: '90px', paddingLeft: '8px', paddingRight: '4px' }}>
              Tokens
            </div>
            <div className="flex-1 flex items-center h-full" style={{ paddingLeft: '2px', paddingRight: '8px' }}>
              Timeline
            </div>
          </div>

          {/* Span rows */}
          {spanTree.map(node => renderSpanNode(node))}
        </div>

        {/* Span Detail Panel */}
        {selectedSpan && (
          <div className="mt-2">
            {renderSpanDetails(selectedSpan)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
