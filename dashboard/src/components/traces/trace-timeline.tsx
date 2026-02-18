import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Clock, Zap, Database, Globe, Bot } from 'lucide-react';
import type { Span } from '../../types';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';

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
const STATUS_COLORS: Record<string, string> = {
  'OK': 'bg-green-500',
  'ERROR': 'bg-red-500',
  'UNSET': 'bg-gray-400',
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
    return { label: 'Workflow', icon: <Zap className="h-3 w-3" />, badgeColor: 'bg-indigo-100 text-indigo-700 border-indigo-200' };
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
        className={`${statusColor} absolute h-6 rounded flex items-center px-1 text-white text-xs font-medium overflow-hidden transition-opacity hover:opacity-90 cursor-pointer shadow-sm`}
        style={{
          left: `${leftPercent}%`,
          width: `${Math.max(widthPercent, 0.5)}%`, // Minimum width for visibility
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
        <div className="flex items-center border-b border-border hover:bg-muted/50 transition-colors">
          {/* Left: Span info with expand button */}
          <div
            className="flex-shrink-0 flex items-center gap-2 py-2 pr-2 min-w-0"
            style={{ width: '350px', paddingLeft: `${depth * 12 + 8}px` }}
          >
            {/* Tree connector line */}
            {depth > 0 && (
              <div className="absolute h-full border-l border-border" style={{ left: `${(depth - 1) * 12 + 8}px` }} />
            )}

            {/* Expand/collapse button */}
            {hasChildren ? (
              <button
                onClick={() => toggleSpan(span.spanId)}
                className="p-0.5 hover:bg-accent rounded flex-shrink-0"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
            ) : (
              <div className="w-5 flex-shrink-0" />
            )}

            {/* Type badge */}
            <Badge variant="outline" className={`${spanType.badgeColor} flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium flex-shrink-0`}>
              {spanType.icon}
              {spanType.label}
            </Badge>

            {/* Span name */}
            <span className="text-sm font-medium truncate" title={span.spanName}>
              {span.spanName}
            </span>
          </div>

          {/* Middle: Metrics */}
          <div className="flex items-center px-3 text-xs text-muted-foreground flex-shrink-0">
            {/* Duration */}
            <div className="flex items-center gap-1" style={{ width: '80px' }}>
              <Clock className="h-3 w-3 flex-shrink-0" />
              <span>{formatDuration(span.duration)}</span>
            </div>

            {/* Tokens (if available) */}
            <div className="flex items-center gap-1" style={{ width: '170px' }}>
              {totalTokens && totalTokens > 0 ? (
                <>
                  <span className="font-mono flex items-center">
                    {isAggregated && <span className="inline-block align-middle mr-1">∑</span>}
                    {totalTokens.toLocaleString()} tokens
                  </span>
                  {inputTokens && outputTokens && inputTokens > 0 && outputTokens > 0 && (
                    <span className="text-muted-foreground/60">
                      ({inputTokens.toLocaleString()}↓ {outputTokens.toLocaleString()}↑)
                    </span>
                  )}
                </>
              ) : (
                <span className="text-muted-foreground/40">—</span>
              )}
            </div>

            {/* Status indicator */}
            <div className="flex items-center justify-center flex-shrink-0" style={{ width: '50px' }}>
              <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[span.statusCode] || STATUS_COLORS['UNSET']}`} title={span.statusCode} />
            </div>
          </div>

          {/* Right: Timeline bar */}
          <div className="flex-1 relative h-10 px-2 min-w-0">
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
      <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
        No traces available
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="p-4">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-base font-semibold">Timeline</h3>
              <span className="text-xs text-muted-foreground">
                {formatDuration(totalDuration * 1_000_000)} · {spans.length} span{spans.length !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Expand/Collapse controls */}
            <div className="flex items-center gap-1">
              <button
                onClick={expandAll}
                className="text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              >
                Expand all
              </button>
              <span className="text-muted-foreground">|</span>
              <button
                onClick={collapseAll}
                className="text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              >
                Collapse all
              </button>
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground mr-1">Status:</span>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-muted-foreground">OK</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-muted-foreground">ERROR</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-gray-400" />
              <span className="text-muted-foreground">UNSET</span>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="border rounded-lg overflow-hidden bg-background">
          {/* Column headers */}
          <div className="flex items-center bg-muted/50 border-b border-border font-medium text-xs text-muted-foreground">
            <div className="flex-shrink-0 px-3 py-2" style={{ width: '350px' }}>
              Span Name
            </div>
            <div className="flex items-center px-3 py-2 flex-shrink-0">
              <span style={{ width: '80px' }}>Duration</span>
              <span style={{ width: '170px' }}>Tokens</span>
              <span style={{ width: '50px', textAlign: 'center' }}>Status</span>
            </div>
            <div className="flex-1 px-2 py-2">
              Timeline
            </div>
          </div>

          {/* Span rows */}
          {spanTree.map(node => renderSpanNode(node))}
        </div>
      </CardContent>
    </Card>
  );
}
