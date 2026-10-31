# AlphaTrion Swarm

The recursive self-improvement system of [AlphaTrion](../../README.md), built on the [framework](../framework/README.md).

Swarm is in early development. Follow the repository for updates, or join the discussion in the issues.

```bash
pip install alphatrion[all]
```

## Concepts

- **Pipeline** - The YAML (or dict) definition of a graph, built with `build_graph()`. It reads like structured code, with no goto:
  - Nodes run in the order they are listed.
  - `branches: {choice: [nodes]}` runs nested nodes for a choice of the node, then continues with the node after it, unless a nested node exits first. A choice with neither a branch nor an exit falls through to the next node; a guardrail's `fail` must have one of them.
  - `exit` leaves the block: `end` finishes the current run and `raise` fails it, and in a loop, `continue` starts the next iteration and `break` ends the loop. Either one exit, like `exit: end`, or a map from chooses exits, like `exit: {fail: continue}`, with an optional `default` key.
- **Graph** - What a pipeline is built into: a directed acyclic graph of nodes. Repetition is always a `loop` node, so a graph without loops always ends. `graph.describe()` shows it as it runs: each node in order, with the format it outputs, its params, with the outputs they reference, its runtime and limits, and where its choices go.
- **Data flow** - Nothing flows implicitly: a node gets another's output only by referencing it in its params, `${nodes.name.output}`, which must be a node that always runs before it with an output, earlier in its block or before it, not one in a branch that may be skipped. The reference's format must fit the parameter's type hint, like `fn(state, code: Files) -> Execution`, checked when the pipeline loads and again when it runs, and a subclass fits wherever its base does. A node has an output only when it makes no choice, its normal path, or one it outputs on, like a loop's `completed`: after a choice its function made, a failure, or for a decision, which only decides, it has none.
- **Params and inputs** - A node function gets exactly what its node's `params` give it, and nothing else: each param is a literal, `${params.name}` for a setting of the pipeline, `${inputs.name}` for an input of the run, or `${nodes.name.output}` for an output. The pipeline's `params` are settings nodes share, and its `inputs` what every run must give, with `graph.run(inputs=...)`; neither reaches a function unless a node references it.

    ```yaml
    params: {command: uv run train.py}
    inputs: [workdir]
    nodes:
      - name: experiment
        type: action
        fn: experiment            # experiment(state, reply, workdir, command, train_timeout)
        params:
          reply: ${nodes.propose.output}
          workdir: ${inputs.workdir}
          command: ${params.command}
          train_timeout: 600
    ```

  In a one-line `{...}`, quote a reference, like `{source: "${inputs.data}"}`, as YAML reads its `{` as a mapping. A parameter its node doesn't give, without a default, is an error when the pipeline loads, and so is a param no function takes, or a reference to a setting or input the pipeline doesn't have. A run missing an input fails before it starts. A subgraph file's params are defaults its parent's override.
- **Formats** - The data formats shared by all nodes, in `alphatrion.swarm.formats`: `Text`, `Files`, `ModelRequest`, `ModelResponse`, `Execution` and `Metrics`. New formats subclass `Format`, and a subclass is accepted wherever its base is, so extending a format never breaks the nodes built on it.
- **Node** - One step of the graph. Built-in types:
  - `action` - Runs a function, e.g. calling an LLM to propose a new artifact. A function returns its output, the format of its return type hint, or makes a choice instead by raising `Choice`, e.g. `raise Choice("skip", "the edits don't apply")` for an exit like `exit: {skip: continue}`, with no output; the reason is recorded in memory. A choice is an outcome, never retried, while any other exception fails the node, on its `error` choice. A check that must never change belongs in a `guardrail`, which is always immutable.
  - `guardrail` - Runs checks and chooses `pass` or `fail`, with the reasons of failed checks as details. `fail` must have an exit or a branch, e.g. `exit: {fail: raise}` to fail the run.
  - `condition` - Chooses `true` or `false` by a function that returns a bool.
  - `switch` - Chooses by a function that returns the name of a case, e.g. which job to run next. The cases are the keys of its `branches` and `exit`; a case without a branch or an exit fails the node, unless a `default` key catches it. An empty case, like `idle: []`, does nothing and continues.
  - `evaluator` - Measures, e.g. the `Execution` its params reference, outputs `Metrics`, and records the primary score on the current artifact.
  - `model_router` - Sends the `ModelRequest` its `request` param references to one of several candidate models, and outputs the `ModelResponse`. A candidate's `options` are extra settings for its model's API, passed as is, like `{output_config: {effort: high}}`. The `weighted` policy picks candidates by weight, and `fallback` tries them in order; a failed attempt, e.g. a timeout or a refusal, moves on to the next candidate. It chooses `ok`, or to `error` when every candidate failed, if handled, and fails otherwise. Claude models use the Anthropic API for `claude-*` ids, with `ANTHROPIC_API_KEY`, or AWS Bedrock for Bedrock's ids, like `us.anthropic.claude-opus-5-5`, with the AWS credentials of the environment and `AWS_REGION`, or a candidate's `region`; both need `pip install alphatrion[anthropic]`. Other models use any OpenAI-compatible API, with `base_url`:

    ```yaml
    - name: prompt
      type: action
      fn: propose_prompt              # fn(state) -> ModelRequest
    - name: propose
      type: model_router
      params:
        request: ${nodes.prompt.output}
      policy: weighted
      candidates:
        - {model: claude-opus-5-5, weight: 0.3}
        - {model: claude-sonnet-5-5, weight: 0.7}
        - {model: llama-4, base_url: "http://localhost:8000/v1", weight: 0.1}
    ```
  - `subgraph` - A node with `nodes`, or a `subgraph` file, and no `type`, runs those nodes as one node, so a coarse step can be detailed one level down and reused. It's written like a pipeline file, a name and its nodes, with the file relative to the pipeline referencing it. It works like a function call: its nodes reference the outputs before it, its output is its last one, an `end` inside returns to the parent, and its nodes are recorded in memory as `<subgraph>.<name>`.

    ```yaml
    - name: attempt                   # inline
      nodes: [...]
    - name: attempt                   # or from a file
      subgraph: attempt.yaml
    ```
  - `loop` - Runs its `nodes` repeatedly, e.g. an agent exploring improvements. Inside, `exit: continue` starts the next iteration and `exit: break` ends the loop. It also ends when `until` returns true after an iteration, or after `max_iters` iterations (`null` loops until cancelled), and chooses `completed` or `max_iters`. An iteration's nodes reference the outputs before the loop and their own, and what carries over is in the tree and the memory. The loop's output is the last output of the last iteration it didn't discard.
  - `parallel` - Runs its `nodes` in `n` concurrent branches, each evolving its own artifact from the current one, then merges them with `join` (`best`, `all`, or a function), whose result is its output. Each branch is its own run, so `end` or `raise` inside one only finishes or fails that branch. `wait: k` joins once k branches finished, ignoring failed ones, and cancels the rest; by default it waits for every branch to finish, and fails if any failed. A branch never stops another: only the parallel node decides when branches stop.
  - Custom decision nodes subclass `DecisionNode` and implement `decide(state) -> (choice, details)`; `condition`, `switch` and `guardrail` are built on it, and have no output.
  - Custom types subclass `Node` with their own `type` and fields, implement `run(state, ...)`, taking what they need as parameters with type hints, like `run(self, state, request: ModelRequest)`, which their `params` give, resolved and checked like a function's, `output_type()` if they have an output, declare `choices` if they choice by name, which checks their `exit` and `branches` keys, and are passed to `build_graph(node_types=[...])`. A node is one class: its fields are its definition, the same in YAML and in code, and `run()` is what it does.

  Each type only accepts its own fields, so a misplaced or misspelled field is an error when the pipeline loads.
- **Capabilities** - What a node may change in the state; reading it is always allowed. `commit` adds artifacts and moves the current one, `remember` writes the memory store, and `score` scores artifacts. Each type has the most its nodes can have: `action` has `commit` and `remember`, `parallel` has `commit` for its join, `evaluator` has `score`, and the others have none, so a `condition`, `switch` or `guardrail` only decides. A node can narrow them, like `capabilities: [commit]`, but never add any. Node functions get the state as a `StateView` limited to them, with a read-only tree, so `commit()` without `commit` raises a `CapabilityError`. Only an evaluator scores, from what its fn measures: `Artifact.score` is frozen, and `commit()` takes no score.
- **Timeouts and retries** - Every node can have a `timeout`, like `60s` or `10m`, and `retries`. A node past its timeout is cancelled, and its runtime stopped, so nothing it ran outlives it. A node that fails, by timing out or raising, runs again up to `retries` times, each from where it started. Still failing, it takes its `timeout` or `error` choice, like `exit: {timeout: continue}`, and the run fails if it doesn't handle it. A choice the node chooses, like a guardrail's `fail`, is an outcome, never retried. Without them, a node has no limit and isn't retried.
- **Runtimes** - Where a node runs its code: the pipeline's `runtimes` name them, each with a `type`, and a node picks one with `runtime: name`. Its functions reach it as `state.runtime`, to `exec` commands and `write` and `read` files, in its `/work` workspace. Each attempt of the node gets a fresh one, stopped when the attempt ends, and killed if it doesn't stop in time.

    ```yaml
    runtimes:
      eval:
        type: microsandbox          # or host, or a backend passed to build_graph(backends=...)
        image: python
        mounts:
          - {path: /data, source: "${inputs.data}"}   # a directory the run is given
          - {path: /code, source: code}             # relative to the pipeline file; read-only by default
    nodes:
      - {name: evaluate, type: action, fn: run, runtime: eval, timeout: 60s}
    ```

  A type names how a runtime runs, not where: the built-in ones are `microsandbox`, hardware-isolated microVMs (`pip install microsandbox`), on this machine or on microsandbox's cloud with `MSB_BACKEND=cloud` and `MSB_API_KEY`, and `host`, processes on this machine without isolation, for development and tests. Mounts bind directories of this machine, so they work on a local microVM but not yet on the cloud. Other backends, e.g. Docker or Kubernetes, subclass `Backend`. The runtimes are part of the fixed root: self-improvement can't change them.
- **Mutability** - Self-improvement may change a node only if it has `mutable: true`; nodes are immutable by default. An immutable node stays as written, its capabilities and nested nodes included, and a mutable one, like a loop, can change around the immutable nodes inside it, but never gain capabilities, loosen its timeout or retries, or change its runtime. Evaluators and guardrails are always immutable, since they judge what counts as an improvement. `check_mutation(original, mutated)` checks a changed pipeline against this, and that no node with `score` was added.
- **Tree** - Records how the artifact evolved. Each artifact derives from its parent, so a graph can branch to explore several variants and backtrack to the best one. `tree.render()` shows it as code evolving: each artifact under the one it came from, with its score and how many lines it changed, the best marked with a star, and `tree.diff(id)` what an artifact changed from its parent, as a unified diff.
- **Tracing** - Every graph run, node attempt and model request is an OpenTelemetry span, with [OpenInference](https://github.com/Arize-ai/openinference)'s conventions, so a model request nests under the node and the run that sent it. A model request is an LLM span with the model, the request, the response and its tokens, whatever the client, and its number in the run. `tracing.setup()` sends the spans to exporters: `HostExporter(path)` for a file of JSON lines on this machine, `DatabaseExporter(path)` for SQLite, with the model and node as columns to query, or any OpenTelemetry exporter, e.g. OTLP to Phoenix, Langfuse or Jaeger. `instrument=True` also traces the Anthropic and OpenAI SDKs themselves, with OpenInference's instrumentors. Without `setup()`, spans go to the application's OpenTelemetry provider, if it has one.

    ```python
    from alphatrion.swarm import tracing

    tracing.setup(tracing.HostExporter("traces.jsonl"))
    ```

  The run itself keeps its requests in `state.requests`, in order, e.g. to check that a router's weights pick the models they should with `state.requests.counts()`. Every attempt is kept, fallbacks included, and a response carries its request's number in `metadata["request"]`, so what it leads to, like an artifact, can link back to it.
- **Experiments and runs** - An experiment is a goal and its judge, improved over runs: it owns the tree of artifacts, the memory and every evaluation's metrics. A run is one execution of a pipeline on it, owning its status, inputs, the pipeline it ran, its requests and its traces. Anything finer, a loop's iteration or a parallel branch, is recorded on what happened in it, e.g. an artifact's `iteration: {research: 4}`, not a level of its own. `graph.run(store=HostStore("experiments", experiment="eplb"))` keeps them on this machine, as the run happens:

    ```
    experiments/eplb/
      experiment.json, tree.json, tree.txt, memory.json, state.json
      artifacts/<id>/        each artifact's files, and diff.patch from its parent
      metrics.jsonl          every evaluation, with its run and iteration
      runs/<run-id>/         run.json (status, inputs fingerprinted, parent), pipeline.txt,
                             requests.jsonl, traces.jsonl with tracing.setup(store.spans())
    ```

  `python -m alphatrion.swarm.show experiments/eplb` shows an experiment in the terminal: its best score, a chart of every evaluation and the best so far, and the tree of artifacts; given an artifact's id, or its start, it shows that artifact's metrics and diff. It reads what the experiment checkpointed, so it works while a run is going.

  `store.load()` returns the experiment's state, to continue it with another run, and `checkpoint_every` saves it every that many iterations of a loop. A run started to evaluate another experiment's artifact, e.g. a pipeline an optimizer proposed, names it with `parent`. Other stores, e.g. for a database, subclass `RunStore`.
- **Memory** - Shared by all nodes: a history of every node execution, plus a key-value store. Memory and the tree can be saved and loaded to continue across runs.
- **State** - Passed to every node, bundling the memory, the tree and the current artifact, which nodes move with `commit()` and `checkout()`. It outlives a run, so a run can continue from it, while inputs belong to each run: `graph.run(state=state, inputs={...})`.

## Example

```yaml
# pipeline.yaml
name: rsi
nodes:
  - name: improve
    type: loop
    max_iters: 50
    until: good_enough
    params:
      target: 0.9
    nodes:
      - name: propose
        type: action
        fn: propose
      - name: guard
        type: guardrail
        checks: [is_valid]
        exit: {fail: continue}
      - name: evaluate
        type: evaluator
        fn: my_package.evals:score  # Functions can also be import paths.
```

To explore with several agents at once, put the loop in a `parallel` node:

```yaml
  - name: explore
    type: parallel
    n: 4
    join: best
    nodes:
      - name: explorer
        type: loop
        # ...
```

```python
from alphatrion.swarm import State, build_graph


async def propose(state: State):
    # Improve on the best artifact so far.
    best = state.tree.best()
    if best is not None:
        state.checkout(best.id)
    feedback = state.memory.history(node="guard", last=1)
    return state.commit(await improve(state.current, feedback)).id


def is_valid(state: State):
    return bool(state.current.content), "artifact is empty"


def good_enough(state: State, target: float):
    return state.current.score >= target


graph = build_graph(
    "pipeline.yaml",
    functions={"propose": propose, "is_valid": is_valid, "good_enough": good_enough},
)
result = await graph.run(inputs={"task": "..."})
print(result.status, result.state.tree.best())
```

Pipelines can also be defined in code with the node classes, which take the same fields as YAML. Functions are passed directly instead of by name, and custom node types work the same way:

```python
from alphatrion.swarm import (
    ActionNode,
    EvaluatorNode,
    GuardrailNode,
    LoopNode,
    Pipeline,
    build_graph,
)

graph = build_graph(
    Pipeline(
        name="rsi",
        nodes=[
            LoopNode(
                name="improve",
                max_iters=50,
                until=good_enough,
                params={"target": 0.9},
                nodes=[
                    ActionNode(name="propose", fn=propose),
                    GuardrailNode(name="guard", checks=[is_valid], exit={"fail": "continue"}),
                    EvaluatorNode(name="evaluate", fn=score),
                ],
            )
        ],
    )
)
```

For full control, build graphs directly with `Graph().add_node(...).add_edge(...)`, with the same node classes.

See the [examples](../../examples) for runnable pipelines, in YAML and in code.

## Design

See the [design doc](./docs/design.md) for how swarm is evolving into a recursive self-improvement agent.
