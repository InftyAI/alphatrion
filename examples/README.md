# Examples

Runnable examples of AlphaTrion. Run them from the repository root after `source start.sh`.

## Basics

How to build and run pipelines, one feature at a time. These need no API keys or services. The artifact is a string evolving toward a target sentence, a stand-in for a prompt or a program that an LLM would improve.

| Example | Shows |
|---|---|
| [improve_loop](./basics/improve_loop) | A pipeline defined in YAML: a `loop` that proposes a variant of the best artifact, rejects duplicates with a `guardrail`, scores it with an `evaluator`, and stops once it is good enough. |
| [condition_branches](./basics/condition_branches) | Conditions and branches in YAML: each iteration a `condition` checks whether progress has stalled, and picks a branch: exploit the best artifact while it improves, or explore from an earlier one once it stalls. Another `condition` breaks the loop with `exit: {true: break}` once solved. |
| [switch_jobs](./basics/switch_jobs) | A `switch` in YAML: each iteration it picks one of several jobs by weight, mutate, crossover or restart, and runs that job's branch. The job that improves the best artifact is credited from memory, so the report shows which jobs pay off. |
| [subgraph](./basics/subgraph) | A subgraph: the pipeline stays coarse, repeating an attempt until solved, and a subgraph node runs `attempt.yaml`, which details one attempt: propose, reject duplicates, evaluate. A rejected duplicate returns early with `exit: end`, and the attempt's nodes are recorded in memory as `attempt.<node>`. |
| [parallel_explore](./basics/parallel_explore) | A pipeline defined in code: four explorers in a `parallel` node, each a `loop` evolving its own lineage in the shared tree and backtracking when a variant is worse, joined by keeping the best. |

```bash
python examples/basics/improve_loop/main.py
python examples/basics/condition_branches/main.py
python examples/basics/switch_jobs/main.py
python examples/basics/subgraph/main.py
python examples/basics/parallel_explore/main.py
```

## Cases

Real self-improvement systems built as pipelines. They need real hardware or credentials; see each one's README for the setup.

| Case | What it improves |
|---|---|
| [eplb](./cases/eplb) | [ADRS's eplb example](https://github.com/UCB-ADRS/ADRS/tree/main/openevolve/examples/ADRS/eplb): a model evolves vLLM's expert parallelism load balancer, scored by ADRS's evaluator on a recorded expert-load trace for balance and speed. It runs on CPU, with torch and an Anthropic API key. |
| [autoresearch](./cases/autoresearch) | [karpathy/autoresearch](https://github.com/karpathy/autoresearch): a model proposes edits to `train.py`, each trains for 5 minutes, and an edit is kept only if `val_bpb` improved. It needs an NVIDIA GPU, e.g. an H100, and an Anthropic API key. |
