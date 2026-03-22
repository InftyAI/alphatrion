# AlphaTrion Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Agent                               │
│                      (Claude Code)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Hook System
                         │ (SessionStart, Stop, SessionEnd)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AlphaTrion Backend                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Hook Handlers (claude.py)                     │ │
│  │  • handle_session_start()  → Create Session               │ │
│  │  • handle_stop()           → Create Run + Spans           │ │
│  │  • handle_session_end()    → Complete Session             │ │
│  └───────────────────────┬────────────────────────────────────┘ │
│                          │                                       │
│          ┌───────────────┴────────────────┐                     │
│          ▼                                ▼                     │
│  ┌──────────────────┐           ┌─────────────────┐            │
│  │   PostgreSQL     │           │   ClickHouse    │            │
│  │   (metadb)       │           │   (tracestore)  │            │
│  │                  │           │                 │            │
│  │  • Teams         │           │  • Spans        │            │
│  │  • Users         │           │  • Traces       │            │
│  │  • Agents        │           │  • Events       │            │
│  │  • Sessions      │           │  • Attributes   │            │
│  │  • Runs          │           │                 │            │
│  └──────────────────┘           └─────────────────┘            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 GraphQL API (server)                       │ │
│  │  • Query sessions, runs, agents                            │ │
│  │  • Query traces with filtering                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/GraphQL
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AlphaTrion Dashboard                          │
│  • React + TypeScript                                            │
│  • Session list, detail views                                   │
│  • Conversation timeline with tool execution details            │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Single Interaction

```
�sequenceDiagram
    participant User
    participant Claude as Claude Code
    participant Hook as Hook Handler
    participant PG as PostgreSQL
    participant CH as ClickHouse

    User->>Claude: "Read main.py"

    Note over Claude: Process request

    Claude->>Claude: Execute Read tool

    Note over Claude: Generate response

    Claude-->>User: "Here's the content..."

    Claude->>Hook: Stop hook (transcript data)

    Hook->>Hook: Parse interaction

    Hook->>PG: Create Run
    Note over PG: Store metadata,<br/>tokens, duration

    Hook->>CH: Create Parent LLM Span
    Note over CH: Store conversation,<br/>prompts, completions

    Hook->>CH: Create Child Tool Span
    Note over CH: Store tool name,<br/>input, output, timing
```

## Span Hierarchy

```
TraceId: abc123
├── Parent Span (SpanId: span-1, ParentSpanId: "")
│   ├── SpanName: anthropic.chat
│   ├── SemanticKind: llm
│   ├── Duration: 3.5s
│   └── Attributes:
│       ├── gen_ai.prompt.0.content: "Read main.py"
│       ├── gen_ai.completion.0.content: "Let me read..."
│       ├── gen_ai.completion.0.tool_calls.0.name: "Read"
│       └── gen_ai.usage.input_tokens: 150
│
└── Child Span (SpanId: span-2, ParentSpanId: span-1)
    ├── SpanName: tool.Read
    ├── SemanticKind: tool
    ├── Duration: 0.15s
    └── Attributes:
        ├── tool.name: "Read"
        ├── tool.input: '{"file_path":"main.py"}'
        ├── tool.output: "<file contents>"
        └── tool.is_error: "false"
```

## Session Lifecycle

```
┌──────────────────┐
│ Claude Code      │
│ Starts           │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────┐
│ SessionStart Hook          │
│ • Create Session           │
│ • Status: RUNNING          │
│ • Store: project, model    │
└────────┬───────────────────┘
         │
         ▼
    ┌────────────────────┐
    │ User Interaction 1 │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────────────┐
    │ Stop Hook                  │
    │ • Create Run #1            │
    │ • Create LLM Span          │
    │ • Create Tool Spans        │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ User Interaction 2 │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────────────┐
    │ Stop Hook                  │
    │ • Create Run #2            │
    │ • Create Spans             │
    └────────┬───────────────────┘
             │
             ▼
         ... more interactions ...
             │
             ▼
┌────────────────────────────┐
│ SessionEnd Hook            │
│ • Update Session           │
│ • Status: COMPLETED        │
└────────────────────────────┘
```

## Storage Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL                               │
│  Optimized for: Relational queries, ACID transactions       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Teams (1)                                                   │
│    └── Users (N)                                             │
│          └── Agents (N)                                      │
│                └── Sessions (N)                              │
│                      └── Runs (N)                            │
│                            • id, session_id, status          │
│                            • duration, created_at            │
│                            • aggregated_tokens               │
│                                                              │
│  Why PostgreSQL?                                             │
│  • Need foreign keys, relationships                          │
│  • Complex queries (JOIN sessions, runs, agents)            │
│  • Aggregations (SUM tokens, AVG duration)                  │
│  • Moderate write volume                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     ClickHouse                               │
│  Optimized for: High-volume writes, analytical queries      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Spans (Millions)                                            │
│    • TraceId, SpanId, ParentSpanId                          │
│    • SpanName, SemanticKind                                 │
│    • Duration, Timestamp                                     │
│    • SpanAttributes (Map<String, String>)                   │
│    • Events, Links                                           │
│    • RunId (links to PostgreSQL)                            │
│                                                              │
│  Why ClickHouse?                                             │
│  • High write throughput (1000s spans/sec)                  │
│  • Fast analytical queries (time-series, filtering)         │
│  • Columnar storage (efficient for attributes)              │
│  • No need for complex joins                                │
└─────────────────────────────────────────────────────────────┘
```

## Query Patterns

```
┌────────────────────────────────────────────────────────┐
│ Pattern 1: Get Session Overview                        │
├────────────────────────────────────────────────────────┤
│ Source: PostgreSQL only                                │
│                                                         │
│ SELECT s.*, COUNT(r.id) as run_count,                  │
│        SUM(r.duration) as total_duration               │
│ FROM sessions s                                         │
│ LEFT JOIN runs r ON r.session_id = s.id               │
│ WHERE s.id = ?                                          │
│ GROUP BY s.id                                           │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Pattern 2: Get Conversation with Tool Details          │
├────────────────────────────────────────────────────────┤
│ Source: PostgreSQL + ClickHouse                        │
│                                                         │
│ Step 1: Get runs from PostgreSQL                       │
│ SELECT * FROM runs WHERE session_id = ?                │
│                                                         │
│ Step 2: Get spans from ClickHouse                      │
│ SELECT * FROM traces                                    │
│ WHERE RunId IN (run_ids)                               │
│ ORDER BY Timestamp                                      │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Pattern 3: Tool Performance Analysis                   │
├────────────────────────────────────────────────────────┤
│ Source: ClickHouse only                                │
│                                                         │
│ SELECT                                                  │
│   SpanAttributes['tool.name'] as tool,                 │
│   COUNT(*) as executions,                              │
│   AVG(Duration) as avg_duration,                       │
│   SUM(CASE WHEN StatusCode = 'ERROR'                   │
│       THEN 1 ELSE 0 END) as errors                     │
│ FROM traces                                             │
│ WHERE SemanticKind = 'tool'                            │
│   AND TeamId = ?                                        │
│ GROUP BY tool                                           │
│ ORDER BY executions DESC                                │
└────────────────────────────────────────────────────────┘
```

## UI Architecture: Message Detail Modal

```
┌─────────────────────────────────────────────────────────┐
│ Session List Page                                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │  Session 1 [12 interactions, 35k tokens]            │ │
│ │  Session 2 [8 interactions, 20k tokens]             │ │
│ │  Session 3 [15 interactions, 42k tokens]            │ │
│ └─────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ Click
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Session Detail Page                                      │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Compact Message List                                │ │
│ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ 👤 Read the file main.py        [2min ago] 🔧1 │ │ │
│ │ ├─────────────────────────────────────────────────┤ │ │
│ │ │ 🤖 Let me read that for you...  [2min ago]     │ │ │
│ │ ├─────────────────────────────────────────────────┤ │ │
│ │ │ 👤 Now edit line 15...          [1min ago] 🔧1 │ │ │
│ │ └─────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ Click message
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Message Detail Modal                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🤖 Assistant Response        [2min ago] 350 tokens │ │
│ │ ─────────────────────────────────────────────────── │ │
│ │                                                     │ │
│ │ Let me read that for you...                         │ │
│ │                                                     │ │
│ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ 🔧 Read                          ⏱️ 150ms       │ │ │
│ │ │ ───────────────────────────────────────────────│ │ │
│ │ │ Input:  {"file_path": "main.py"}                │ │ │
│ │ │ Output: <file contents...>                       │ │ │
│ │ └─────────────────────────────────────────────────┘ │ │
│ │                                                     │ │
│ │ Here's the content of main.py...                    │ │
│ │                                                     │ │
│ │ ─────────────────────────────────────────────────── │ │
│ │ ⏱️ 2024-03-18 14:30:15  ⚡ 150 in • 200 out       │ │
│ │                                                     │ │
│ │ [Previous]  1 / 33  [Next]                [Close]  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```
