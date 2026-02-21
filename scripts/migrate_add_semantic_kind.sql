-- Migration script to add SemanticKind column to existing otel_spans table
-- This should be run on existing ClickHouse databases

-- Step 1: Add SemanticKind column
ALTER TABLE alphatrion_traces.otel_spans
ADD COLUMN IF NOT EXISTS SemanticKind LowCardinality(String) DEFAULT '' CODEC(ZSTD(1));

-- Step 2: Populate SemanticKind for existing rows
-- This determines the semantic kind based on span attributes
ALTER TABLE alphatrion_traces.otel_spans
UPDATE SemanticKind =
    CASE
        WHEN mapContains(SpanAttributes, 'llm.usage.total_tokens') THEN 'llm'
        WHEN mapContains(SpanAttributes, 'traceloop.span.kind') THEN SpanAttributes['traceloop.span.kind']
        ELSE 'unknown'
    END
WHERE SemanticKind = '';

-- Step 3: Add index for efficient filtering
ALTER TABLE alphatrion_traces.otel_spans
ADD INDEX IF NOT EXISTS idx_semantic_kind SemanticKind TYPE set(0) GRANULARITY 1;

-- Verify the migration
SELECT SemanticKind, COUNT(*) as count
FROM alphatrion_traces.otel_spans
GROUP BY SemanticKind
ORDER BY count DESC;
