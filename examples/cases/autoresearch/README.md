# autoresearch

[autoresearch](https://github.com/karpathy/autoresearch) as a pipeline: a model proposes an edit to `train.py`, it trains for a fixed 5 minutes, and the edit is kept if `val_bpb` improved, else reverted. It runs until stopped.

```
baseline        -> Execution      action  params: workdir=${inputs.workdir}, command=${params.command}, train_timeout=${params.train_timeout}  runtime: train  choices: crashed -> raise
score_baseline  -> Metrics        evaluator  params: run=${nodes.baseline.output}
research        -> Files          loop
  prompt        -> ModelRequest   action  params: instructions=${inputs.instructions}, workdir=${inputs.workdir}
  propose       -> ModelResponse  model_router  params: request=${nodes.prompt.output}  choices: error -> continue
  experiment    -> Execution      action  params: reply=${nodes.propose.output}, workdir=${inputs.workdir}, command=${params.command}, train_timeout=${params.train_timeout}  runtime: train  choices: skip -> continue, crashed -> continue
  evaluate      -> Metrics        evaluator  params: run=${nodes.experiment.output}
  settle        -> Files          action  params: metrics=${nodes.evaluate.output}, workdir=${inputs.workdir}
```

This is `graph.describe()`: what each step outputs, what it's given, with the outputs it references, its runtime and limits, and where its choices go.

- [pipeline.yaml](./pipeline.yaml) - The pipeline.
- [autoresearch.py](./autoresearch.py) - What each node does: git, the training run, and `results.tsv`.
- [proposer.md](./proposer.md) - The instructions for the model, after autoresearch's `program.md`. The model replies with search/replace edits to `train.py`, which are applied only if each matches the current file exactly.

Each experiment is a commit on an `autoresearch/<tag>` branch: a kept one stays, and a discarded or crashed one is reset. `results.tsv` in the repo, untracked, logs every experiment in autoresearch's format.

## Run on a GPU

autoresearch needs one NVIDIA GPU, e.g. an H100, and [uv](https://docs.astral.sh/uv/).

```bash
# autoresearch, with its data prepared once
git clone https://github.com/karpathy/autoresearch ~/autoresearch
cd ~/autoresearch && uv sync && uv run prepare.py && uv run train.py

# alphatrion, with Claude support
pip install "alphatrion[anthropic]"
export ANTHROPIC_API_KEY=...

# From the alphatrion repository root
python examples/cases/autoresearch/main.py --repo ~/autoresearch
```

It runs until stopped with Ctrl-C, about 12 experiments an hour, and prints `results.tsv` and the best experiment. Use `--iterations N` to stop after N experiments, `--tag` to name the branch, and `--program` to use other instructions. Edit `pipeline.yaml` to change the models, their weights or the effort.
