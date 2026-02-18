import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Clock } from 'lucide-react';
import type { Span } from '../../types';
import { Card, CardContent } from '../ui/card';

interface TraceTimelineProps {
  spans: Span[];
}

interface SpanNode {
  span: Span;
  children: SpanNode[];
  depth: number;
}

// Status color mapping
const STATUS_COLORS: Record<string, string> = {
  'OK': 'bg-green-500',
  'ERROR': 'bg-red-500',
  'UNSET': 'bg-gray-400',
};

// Span kind colors
const KIND_COLORS: Record<string, string> = {
  'INTERNAL': 'bg-blue-500',
  'SERVER': 'bg-purple-500',
  'CLIENT': 'bg-cyan-500',
  'PRODUCER': 'bg-orange-500',
  'CONSUMER': 'bg-pink-500',
};

export function TraceTimeline({ spans }: TraceTimelineProps) {
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set());

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

    sortChildren(rootSpans);
    return rootSpans;
  }, [spans]);

  // Calculate timeline dimensions
  const { minTimestamp, maxTimestamp, totalDuration } = useMemo(() => {
    if (!spans || spans.length === 0) {
      return { minTimestamp: 0, maxTimestamp: 0, totalDuration: 0 };
    }

    const timestamps = spans.map(s => new Date(s.timestamp).getTime());
    const min = Math.min(...timestamps);
    const max = Math.max(...timestamps);
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
    const kindColor = KIND_COLORS[span.spanKind] || KIND_COLORS['INTERNAL'];

    return (
      <div
        className={`${kindColor} absolute h-6 rounded flex items-center px-1 text-white text-xs font-medium overflow-hidden transition-opacity hover:opacity-90 cursor-pointer shadow-sm`}
        style={{
          left: `${leftPercent}%`,
          width: `${Math.max(widthPercent, 0.5)}%`, // Minimum width for visibility
        }}
        title={`${span.spanName}\nDuration: ${formatDuration(span.duration)}\nStatus: ${span.statusCode}`}
      >
        <span className="truncate">{formatDuration(span.duration)}</span>
      </div>
    );
  };

  const renderSpanNode = (node: SpanNode): JSX.Element => {
    const { span, children, depth } = node;
    const hasChildren = children.length > 0;
    const isExpanded = expandedSpans.has(span.spanId);

    return (
      <div key={span.spanId}>
        {/* Span Row */}
        <div className="flex items-center border-b border-border hover:bg-muted/50 transition-colors">
          {/* Left: Span name with expand button */}
          <div
            className="flex-shrink-0 flex items-center gap-1 py-2 pr-2"
            style={{ width: '300px', paddingLeft: `${depth * 20 + 8}px` }}
          >
            {hasChildren ? (
              <button
                onClick={() => toggleSpan(span.spanId)}
                className="p-0.5 hover:bg-accent rounded"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
            ) : (
              <div className="w-5" />
            )}
            <span className="text-sm font-medium truncate" title={span.spanName}>
              {span.spanName}
            </span>
          </div>

          {/* Right: Timeline bar */}
          <div className="flex-1 relative h-10 px-2">
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
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-base font-semibold">Trace Timeline</h3>
            <span className="text-xs text-muted-foreground">
              ({spans.length} span{spans.length !== 1 ? 's' : ''})
            </span>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-500" />
              <span className="text-muted-foreground">OK</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-red-500" />
              <span className="text-muted-foreground">ERROR</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span className="text-muted-foreground">INTERNAL</span>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="border rounded-lg overflow-hidden bg-background">
          {spanTree.map(node => renderSpanNode(node))}
        </div>

        {/* Summary */}
        <div className="mt-4 text-xs text-muted-foreground">
          Total duration: {formatDuration(totalDuration * 1_000_000)}
        </div>
      </CardContent>
    </Card>
  );
}
