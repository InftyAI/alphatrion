# Swarm design: a recursive self-improvement agent

Status: draft for discussion.

## Goal

Swarm improves an **agent**: its prompts, its code, and the procedure it uses to improve itself. The last part is what makes it recursive. Systems such as AlphaEvolve, OpenEvolve, ADAS, AFlow and GEPA optimize a task artifact with a fixed improver. Systems such as the Darwin Gödel Machine (DGM), SICA, the Huxley-Gödel Machine (HGM), Gödel Agent and STOP put the improver inside the search space, so a better agent is also a better improver. Swarm targets the second kind and also supports the first, which is the same loop with a frozen improver.

## Lessons from the community

| Source | What we take | What we avoid |
|---|---|---|
| AlphaEvolve / OpenEvolve | Async proposal workers over a shared program database. Cascade evaluation from cheap to expensive. Evaluator artifacts (stderr, profiles) fed back into prompts. A YAML config with a seed. | Keep-the-best greedy search. |
| DGM | An open-ended archive that keeps every valid agent, so a weak branch can lead somewhere later. Selection favors good but under-explored parents. A child is written by its parent, using the parent's own failure logs. A "can still self-modify" gate. | Letting the agent touch its own evaluation; DGM observed objective hacking. |
| HGM | Score a node by how well its *descendants* do (clade metaproductivity), not only by its own score. A high benchmark score doesn't mean an agent is good at improving itself. | |
| SICA | The best agent so far becomes the next improver. Cost and time are part of the utility. An async overseer can cancel a run that is looping or drifting. | |
| ShinkaEvolve | Pluggable parent selection (weighted, power law, beam). Novelty rejection by embedding similarity. Periodic meta-recommendations. Genealogy kept in a database. | |
| GEPA / Reflexion / ACE | Rich textual feedback alongside scores. A reflection step that writes lessons to memory. A bounded, curated memory instead of an ever-growing context. | Context bloat. |
| STOP | | The improver disabled its own sandbox flag. Guardrails and the sandbox must be outside the mutable surface. |
| LangGraph | A graph with conditional edges and bounded loops. Per-run checkpoints kept separate from a cross-run memory store. | One global state any node can write, which makes data flow implicit. |
| pydantic-graph / MS Agent Framework | Typed node inputs and outputs, checked by the engine. | |
| OpenAI Agents SDK / Google ADK | Guardrails that return a typed verdict and raise a tripwire on hard failure. Global before/after hooks for cross-cutting policy. Scoped state keys. | |
| Dify / n8n | Explicit `node.field` references in YAML, so dependencies are visible and checked at load time. Functions referenced by import path. | Code embedded in YAML. |

## Architecture

```
                    ┌──────────────────── Pipeline (YAML) ────────────────────┐
                    │ nodes, selection, budget, protected surface, ...        │
                    └────────────────────────────┬────────────────────────────┘
                                                 │ build + validate
┌───────────────────────── Engine ─────────────────────────────────────────────┐
│  Worker 1..N, each running one iteration of the graph:                      │
│                                                                             │
│   select ─► context ─► propose ─► guardrails ─► evaluate (cascade) ─► archive│
│     ▲                                 │ fail          │ reject          │     │
│     └─────────────────────────────────┴───────────────┴──── reflect ◄───┘     │
│                                                                             │
│  Hooks: budget, audit, overseer, tracing (before/after every node)          │
└──────────────┬──────────────────────────────┬───────────────────────────────┘
               │                              │
        ┌──────▼──────┐               ┌───────▼────────┐
        │    Tree     │               │     Memory     │
        │ (archive of │               │ run / experiment│
        │  agents)    │               │ / global scopes │
        └──────┬──────┘               └───────┬────────┘
               └──────────── framework ───────┘
          Experiment, Run per candidate, log_metrics, log_artifact, tracing
```

The design has five parts: the artifact and the tree, nodes, the graph and the engine, memory, and the pipeline.

### 1. Artifact and tree

An **artifact** is one version of the agent being improved:

```python
class Artifact(BaseModel):
    id: str
    parent_id: str | None
    content: dict[str, str]          # files: prompts, code, the agent's own improver
    status: Literal["proposed", "rejected", "evaluated"]
    metrics: dict[str, float]        # e.g. accuracy, cost, latency
    score: float | None              # the combined objective
    feedback: str | None             # textual feedback from guardrails and evaluation
    created_by: str | None           # node, model, and the id of the improver artifact
    metadata: dict[str, Any]
```

- Rejected artifacts stay in the tree, so the agent can learn from failures. Selection only picks evaluated ones.
- `content` is a set of files rather than a single value, so an artifact can hold an agent's prompts and code together.

The **tree** is the archive. Its lineage, scores and child counts are what parent selection works from. Selection is a pluggable strategy:

| Strategy | Picks | From |
|---|---|---|
| `best` | the top-scoring artifact | SICA, greedy |
| `weighted` | proportional to sigmoid(score) / (1 + children) | DGM, ShinkaEvolve |
| `power_law` | by rank, with exponent α | ShinkaEvolve |
| `clade` | by the aggregated scores of each artifact's descendants | HGM |
| `pareto` | from the per-objective Pareto front | GEPA |

Each strategy also returns a few **inspirations**: top-scoring and diverse peers to show the proposer. Islands (separate sub-populations, as in AlphaEvolve) are left for later; the tree API should not rule them out.

### 2. Nodes

A node is a typed function: it declares its `Input` and `Output` as pydantic models.

```python
class Node(ABC, Generic[I, O]):
    type: str
    Input: ClassVar[type[BaseModel]]
    Output: ClassVar[type[BaseModel]]

    async def run(self, ctx: Context, input: I) -> O: ...   # the work
    def route(self, output: O) -> str | None: ...           # picks the outgoing edge
    routes: ClassVar[set[str]]                              # declared, so edges are checked
```

- `run` does the work and `route` decides control flow; the two stay separate.
- `routes` lists every route a node can return, so the pipeline loader can check that each one has an edge.
- `Context` carries what the whole run shares: run inputs, the tree, memory, the budget, and the sandbox.
- The data a node consumes comes through `Input`.
- Common policies sit on the base class: `retry`, `timeout`, `cache`.

Built-in node types, in the order they appear in the loop:

| Type | Input → Output | Routes | Notes |
|---|---|---|---|
| `select` | strategy params → `parent`, `inspirations` | | Wraps a selection strategy. |
| `context` | `parent`, `inspirations` → `prompt` | | Adds lineage, evaluator feedback, and lessons retrieved from memory. Bounded by a token budget. |
| `propose` | `parent`, `prompt` → `candidate` | | Calls the LLM. In recursive mode it runs the **parent's own improver** in the sandbox. The output is a diff or a full rewrite. |
| `guardrail` | `candidate` → `passed`, `reasons` | `pass` / `fail` | Blocking. Hard failures raise a tripwire. |
| `evaluate` | `candidate` → `metrics`, `score`, `feedback` | `accept` / `reject` | A cascade: each stage has a threshold, and a candidate that misses one stops early. |
| `archive` | `candidate`, `metrics` → `artifact` | | Commits to the tree. This is the only node that writes the tree. |
| `reflect` | `artifact`, `feedback` → `lesson` | | Writes a lesson to memory. |
| `condition` | any → `value` | declared labels | Routing. |
| `action` | user function → user output | | Escape hatch. Its I/O schema is derived from the function signature. |

Guardrails appear in two places:
- As **nodes**, for checks on a specific candidate: syntax, the protected surface, novelty, "can still self-improve".
- As **hooks**, for policy that applies across every node: budget, the overseer, audit logging.

Hook guardrails can short-circuit any node, the way Google ADK callbacks do.

### 3. Graph and engine

- **Wiring.** Pipelines connect nodes with explicit references such as `evaluate.score` or `inputs.task`. The loader resolves every reference against the target node's `Output` schema when the pipeline loads. Edges with `when` handle control flow; loops are bounded.
- **Parallelism.** It lives at the iteration level, not inside the graph. The engine runs N workers concurrently, each running one iteration of the graph, and all of them share the tree and memory. This is AlphaEvolve's async pipeline, and it avoids fan-out and join semantics inside the graph. The tree serializes writes.
- **Stopping.** The engine stops when any of these is hit:
  - `max_iterations`
  - `budget.max_cost` (USD, taken from the framework's tracing cost data)
  - `target_score`
  - stagnation, meaning no improvement in K iterations

  These mirror the framework's `ExperimentConfig` (early stopping, target metric value), so the two can share semantics.
- **Checkpointing.** The engine saves after every archive step. Resuming reloads the tree and memory. Nodes must be idempotent, because a resumed iteration re-runs from `select`.

### 4. Memory

Memory has three layers, kept separate:

| Layer | Lifetime | Contents |
|---|---|---|
| Run state | One iteration | Node outputs, resolved by references. Recorded to history. |
| History | One experiment | Every node execution: inputs, outputs, route, cost. An audit log that is also used for debugging. |
| Long-term store | Across experiments | Namespaced entries: `lessons/`, `failures/`, `meta/`. Written explicitly by `reflect` and meta nodes, and read through bounded retrieval (top-k by recency and relevance). |

Long-term memory is written on purpose, never as a side effect of state. The store is an interface, so the in-memory and JSON backends can later be replaced by a database or a vector store.

### 5. Pipeline

```yaml
name: improve-coding-agent
seed: 42
budget: {max_cost: 50.0}

agent:
  seed_path: ./agents/seed            # the initial artifact
  improver: self                      # recursive mode; or a fixed path to optimize the task only
  protected: [evals/**, pipeline.yaml]

selection: {strategy: weighted, sharpness: 10, inspirations: {top: 3, diverse: 2}}

nodes:
  - name: workers
    type: parallel
    n: 4                              # four explorers sharing the tree
    join: best
    nodes:
      - name: explore
        type: loop
        max_iters: 50
        until: swarm.stop:target_or_stagnation
        params: {target_score: 0.8, stagnation: 30}
        nodes:                        # each node falls through to the next
          - {name: select, type: select}
          - name: context
            type: context
            inputs: {parent: select.parent, inspirations: select.inspirations}
            params: {max_tokens: 20000, lessons: 5}
          - name: propose
            type: propose
            inputs: {parent: select.parent, prompt: context.prompt}
            params: {models: [{name: claude-sonnet-5-5, weight: 0.8}, {name: claude-opus-5-5, weight: 0.2}]}
          - name: guard
            type: guardrail
            inputs: {candidate: propose.candidate}
            checks: [swarm.checks:syntax, swarm.checks:protected_surface, swarm.checks:novelty]
            branches:
              fail:                   # rejected candidates are archived too
                - name: archive_rejected
                  type: archive
                  inputs: {candidate: propose.candidate}
                  exit: continue
              pass:
                - name: evaluate
                  type: evaluate
                  inputs: {candidate: propose.candidate}
                  stages:
                    - {fn: my_evals:smoke, threshold: 0.2}
                    - {fn: my_evals:full}
          - name: archive
            type: archive
            inputs: {candidate: propose.candidate, metrics: evaluate.metrics}
          - name: reflect
            type: reflect
            inputs: {artifact: archive.artifact, feedback: evaluate.feedback}
```

Nodes run in list order. `guard` nests what each route runs: a rejected candidate is archived and the loop continues, and a candidate that passes is evaluated, then continues to `archive` and `reflect`. The `loop` and `parallel` nodes already exist. `select`, `context`, `propose`, `evaluate`, `archive`, `reflect`, `inputs` references, and the `budget`, `agent` and `selection` sections are still to be built.

## Safety

Systems that improve themselves have tampered with their own objectives: STOP disabled its sandbox flag, and DGM removed the markers used to detect hallucinated tool use. These rules are not negotiable:

1. **A protected surface.** The evaluator, the guardrails, the budget and the pipeline are outside the artifact. A built-in guardrail rejects any candidate whose diff touches `protected` paths, and the engine never loads them from an artifact.
2. **A sandbox.** Proposals and evaluations of agent code run in a sandbox: a subprocess with limits first, Docker later. The sandbox settings are not visible to the agent.
3. **A held-out evaluation set.** The final `score` comes from tasks that are never shown in proposer feedback, which limits overfitting and reward hacking.
4. **An audit trail.** Every artifact records its lineage, its diff, the improver that produced it, and the guardrail results.
5. **An overseer hook and budget hook.** Both can cancel a run.

## Integration with the framework

- A pipeline run is an `Experiment`; each candidate is a `Run`.
- Metrics go through `log_metrics`. The experiment's `monitor_metric` is the pipeline score, so the dashboard shows progress for free.
- Notable artifacts (the best one, and checkpoints) are pushed with `log_artifact`.
- Every node execution is a tracing span. LLM token and cost tracking comes from the existing instrumentation and feeds the budget hook.
- The swarm imports the framework, never the other way around; the import-linter contract enforces this.

## Mapping to the current code

| Today | Planned |
|---|---|
| `Tree`, `Artifact` (single `content`, single `score`) | Add `status`, `metrics`, `feedback`, and file-set `content`; add selection strategies and clade scores. |
| `nodes/` (action, condition, guardrail, evaluator) | Typed `Input`/`Output`, declared `routes`, base policies; add `select`, `context`, `propose`, `archive`, `reflect`; turn `evaluator` into the cascade `evaluate`. |
| `Graph` (single loop, `State`) | One iteration per worker, a `Context` replacing `State`, reference resolution, hooks, an engine running N workers. |
| `memory/` (history plus key-value) | Split into history and a namespaced long-term store with retrieval. |
| `pipeline.py` | Add references, selection, budget, stop, agent and protected-surface sections. |

## Phases

1. **Core contracts.** Typed node I/O, references, `Context`, hooks; the artifact and tree upgrades; a single worker.
2. **Optimizer mode.** Built-in `select`, `context`, `propose`, `evaluate`, `archive`, `reflect` nodes with a fixed improver; framework integration. At this point it is comparable to OpenEvolve and GEPA.
3. **Recursive mode.** `improver: self`, the sandbox, the protected surface, and the "can still self-improve" gate. At this point it is comparable to DGM and SICA.
4. **Scale and search.** N workers, clade selection, novelty filtering, islands, and meta-recommendations.

## Open questions

1. Is the target artifact always a coding agent (files plus a run command), or should prompt-only agents be a first-class case?
2. Which sandbox first: subprocess with resource limits, or Docker from the start?
3. Should the long-term store live in the framework (Postgres, ClickHouse), so the dashboard can show lessons and lineage, or stay inside swarm for now?
4. Is the meta level only `improver: self`, or should the agent also be allowed to edit parts of the pipeline, such as selection params and prompt templates, under a guardrail?
