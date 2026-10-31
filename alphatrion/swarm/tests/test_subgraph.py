import pytest

from alphatrion.swarm import (
    END,
    ActionNode,
    Execution,
    Files,
    Graph,
    GraphStatus,
    Metrics,
    SubgraphNode,
    build_graph,
)


def read(state) -> Files:
    return Files(files={"train.py": "lr = 1"})


def run(state, code: Files) -> Execution:
    return Execution(exit_code=0, stdout="val_bpb: 0.9", duration=1.0)


def measure(state, result: Execution) -> Metrics:
    return Metrics(values={"val_bpb": 0.9}, primary="val_bpb", lower_is_better=True)


FUNCTIONS = {"read": read, "run": run, "measure": measure}

EXPERIMENT = """
name: experiment
nodes:
  - {name: run, type: action, fn: run, params: {code: "${nodes.read.output}"}}
  - {name: measure, type: action, fn: measure, params: {result: "${nodes.run.output}"}}
"""


@pytest.mark.asyncio
async def test_inline_subgraph():
    pipeline = {
        "nodes": [
            {"name": "read", "type": "action", "fn": "read"},
            {
                # No type: a node with nodes is a subgraph.
                "name": "experiment",
                # Its nodes reference the outputs before it, and their own.
                "nodes": [
                    {
                        "name": "run",
                        "type": "action",
                        "fn": "run",
                        "params": {"code": "${nodes.read.output}"},
                    },
                    {
                        "name": "measure",
                        "type": "action",
                        "fn": "measure",
                        "params": {"result": "${nodes.run.output}"},
                    },
                ],
            },
        ]
    }
    graph = build_graph(pipeline, functions=FUNCTIONS)
    assert isinstance(graph.nodes["experiment"], SubgraphNode)
    node = graph.nodes["experiment"]
    # Its output is that of its last node.
    assert node.output_type() is Metrics

    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED
    assert result.output.score == 0.9
    # Its nodes are recorded in memory under its name.
    assert [e.node for e in result.state.memory] == [
        "read",
        "experiment.run",
        "experiment.measure",
        "experiment",
    ]


@pytest.mark.asyncio
async def test_subgraph_from_a_file_used_twice(tmp_path):
    (tmp_path / "steps").mkdir()
    (tmp_path / "steps" / "experiment.yaml").write_text(EXPERIMENT)
    (tmp_path / "pipeline.yaml").write_text(
        """
nodes:
  - {name: read, type: action, fn: read}
  - {name: first, subgraph: steps/experiment.yaml}
  - {name: back, type: action, fn: read}
  - {name: second, subgraph: steps/experiment.yaml}
"""
    )
    result = await build_graph(tmp_path / "pipeline.yaml", functions=FUNCTIONS).run()
    assert result.status == GraphStatus.COMPLETED
    nodes = [e.node for e in result.state.memory]
    # The same file twice, each with its own scope.
    assert "first.run" in nodes and "second.run" in nodes


def test_nested_files_resolve_relative_to_their_referrer(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "outer.yaml").write_text(
        "nodes:\n  - {name: inner, subgraph: ../inner.yaml}\n"
    )
    (tmp_path / "inner.yaml").write_text(EXPERIMENT)
    (tmp_path / "pipeline.yaml").write_text(
        """
nodes:
  - {name: read, type: action, fn: read}
  - {name: outer, subgraph: a/outer.yaml}
"""
    )
    graph = build_graph(tmp_path / "pipeline.yaml", functions=FUNCTIONS)
    assert graph.nodes["outer"].output_type() is Metrics


@pytest.mark.asyncio
async def test_end_returns_to_the_parent():
    def done(state, code: Files) -> Files:
        return code

    experiment = SubgraphNode(
        name="experiment",
        nodes=[
            ActionNode(
                name="done",
                fn=done,
                params={"code": "${nodes.read.output}"},
                exit="end",
            ),
            ActionNode(name="never", fn=run, params={"code": "${nodes.read.output}"}),
        ],
    )
    graph = (
        Graph()
        .add_node(ActionNode(name="read", fn=read))
        .add_node(experiment)
        .add_node(
            ActionNode(name="run", fn=run, params={"code": "${nodes.read.output}"})
        )
        .add_edge("read", "experiment")
        .add_edge("experiment", "run")
        .add_edge("run", END)
    )
    result = await graph.run()
    assert result.path == ["read", "experiment", "run"]
    assert "experiment.never" not in [e.node for e in result.state.memory]


def test_loop_exits_dont_cross_a_subgraph():
    pipeline = {
        "nodes": [
            {
                "name": "loop",
                "type": "loop",
                "max_iters": 2,
                "nodes": [
                    {
                        "name": "experiment",
                        "nodes": [
                            {
                                "name": "a",
                                "type": "action",
                                "fn": "read",
                                "exit": "continue",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    with pytest.raises(ValueError, match="only allowed in a loop"):
        build_graph(pipeline, functions=FUNCTIONS)


def test_invalid_subgraphs(tmp_path):
    # A pipeline that includes itself.
    (tmp_path / "pipeline.yaml").write_text(
        "nodes:\n  - {name: again, subgraph: pipeline.yaml}\n"
    )
    with pytest.raises(ValueError, match="includes itself"):
        build_graph(tmp_path / "pipeline.yaml", functions=FUNCTIONS)

    # A reference from inside is checked like any: read outputs Files, but
    # measure takes an Execution.
    pipeline = {
        "nodes": [
            {"name": "read", "type": "action", "fn": "read"},
            {
                "name": "experiment",
                "nodes": [
                    {
                        "name": "measure",
                        "type": "action",
                        "fn": "measure",
                        "params": {"result": "${nodes.read.output}"},
                    }
                ],
            },
        ]
    }
    with pytest.raises(
        ValueError,
        match=r"takes Execution, but \$\{nodes.read.output\} is Files",
    ):
        build_graph(pipeline, functions=FUNCTIONS)

    with pytest.raises(ValueError, match="either nodes or subgraph"):
        SubgraphNode(name="g")


@pytest.mark.asyncio
async def test_failure_inside_fails_the_parent():
    def broken(state, code: Files) -> Execution:
        raise ValueError("boom")

    experiment = SubgraphNode(
        name="experiment",
        nodes=[
            ActionNode(
                name="broken", fn=broken, params={"code": "${nodes.read.output}"}
            )
        ],
    )
    graph = (
        Graph()
        .add_node(ActionNode(name="read", fn=read))
        .add_node(experiment)
        .add_edge("read", "experiment")
    )
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert "Subgraph experiment failed" in result.error and "boom" in result.error
