import pytest
import yaml

from alphatrion.swarm import GraphStatus, Text, build_graph


def read(state, path: str) -> Text:
    return Text(content=f"read {path}")


def wait(state, text: Text, timeout: int) -> Text:
    return Text(content=f"{text.content}, waited {timeout}")


def check(state, text: Text, timeout: int, retries: int = 1) -> Text:
    return Text(content=f"{text.content}, checked {timeout}x{retries}")


def pause(state, timeout: int) -> int:
    return timeout


FUNCTIONS = {fn.__name__: fn for fn in (read, wait, check, pause)}


def build(pipeline: str):
    return build_graph(yaml.safe_load(pipeline), functions=FUNCTIONS)


@pytest.mark.asyncio
async def test_a_function_gets_exactly_its_node_s_params():
    graph = build(
        """
        params: {timeout: 60}
        inputs: [path]
        nodes:
          - {name: read, type: action, fn: read, params: {path: "${inputs.path}"}}
          - name: wait
            type: action
            fn: wait
            params: {text: "${nodes.read.output}", timeout: "${params.timeout}"}
          - name: check
            type: action
            fn: check
            params: {text: "${nodes.wait.output}", timeout: 5}
        """
    )
    result = await graph.run(inputs={"path": "data/"})
    assert result.status == GraphStatus.COMPLETED, result.error
    # wait references the pipeline's timeout, check gives a literal and keeps
    # its default retries: nothing reaches a function its node doesn't give.
    assert result.output.content == "read data/, waited 60, checked 5x1"


def test_params_are_checked_when_built():
    cases = [
        # A parameter the node doesn't give.
        (
            "nodes: [{name: w, type: action, fn: pause}]",
            "function pause takes 'timeout', which the node doesn't give",
        ),
        # A pipeline param isn't given implicitly, only by reference.
        (
            "params: {timeout: 60}\nnodes: [{name: w, type: action, fn: pause}]",
            "doesn't give",
        ),
        # A param the function doesn't take.
        (
            "nodes: [{name: w, type: action, fn: pause, params: {timeout: 1, tmeout: 2}}]",
            "params it doesn't take: tmeout",
        ),
        # References to what the pipeline doesn't declare.
        (
            'nodes: [{name: w, type: action, fn: pause, params: {timeout: "${params.timeout}"}}]',
            r"is \$\{params.timeout\}, which is not a param",
        ),
        (
            'nodes: [{name: r, type: action, fn: read, params: {path: "${inputs.path}"}}]',
            r"is \$\{inputs.path\}, which is not an input",
        ),
        # A malformed reference.
        (
            'params: {t: 1}\nnodes: [{name: w, type: action, fn: pause, params: {timeout: "${param.t}"}}]',
            "a reference is",
        ),
    ]
    for pipeline, error in cases:
        with pytest.raises(ValueError, match=error):
            build(pipeline)


@pytest.mark.asyncio
async def test_a_run_missing_inputs_fails_before_running():
    graph = build(
        """
        inputs: [path]
        nodes: [{name: read, type: action, fn: read, params: {path: "${inputs.path}"}}]
        """
    )
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert result.error == "The run is missing inputs: path"
    assert result.path == []


@pytest.mark.asyncio
async def test_inputs_belong_to_the_run_not_the_state():
    graph = build(
        """
        inputs: [path]
        nodes: [{name: read, type: action, fn: read, params: {path: "${inputs.path}"}}]
        """
    )
    first = await graph.run(inputs={"path": "a/"})
    # The same state, continued with other inputs.
    second = await graph.run(state=first.state, inputs={"path": "b/"})
    assert (first.output.content, second.output.content) == ("read a/", "read b/")
    assert not hasattr(second.state, "inputs")
    # A later run without them is missing them, rather than reusing the last.
    third = await graph.run(state=second.state)
    assert third.error == "The run is missing inputs: path"


def where(state, path: str):
    state.commit(path)


@pytest.mark.asyncio
async def test_inputs_reach_loops_and_parallel_branches():
    step = {
        "name": "where",
        "type": "action",
        "fn": "where",
        "params": {"path": "${inputs.path}"},
    }
    graph = build_graph(
        {
            "inputs": ["path"],
            "nodes": [
                {**step, "name": "root"},
                {
                    "name": "explore",
                    "type": "parallel",
                    "n": 2,
                    "join": "all",
                    "nodes": [
                        {
                            "name": "repeat",
                            "type": "loop",
                            "max_iters": 2,
                            "nodes": [step],
                        }
                    ],
                },
            ],
        },
        functions={"where": where},
    )
    result = await graph.run(inputs={"path": "data/"})
    assert result.status == GraphStatus.COMPLETED, result.error
    # The root, then two iterations in each of the two branches.
    assert [a.content for a in result.state.tree] == ["data/"] * 5


@pytest.mark.asyncio
async def test_subgraph_files_take_the_parent_s_params(tmp_path):
    (tmp_path / "step.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "step",
                "params": {"timeout": 1, "retries": 2},
                "nodes": [
                    {
                        "name": "check",
                        "type": "action",
                        "fn": "check",
                        "params": {
                            # read, before the subgraph, in the parent.
                            "text": "${nodes.read.output}",
                            "timeout": "${params.timeout}",
                            "retries": "${params.retries}",
                        },
                    }
                ],
            }
        )
    )
    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(
            {
                "params": {"timeout": 60},
                "inputs": ["path"],
                "nodes": [
                    {
                        "name": "read",
                        "type": "action",
                        "fn": "read",
                        "params": {"path": "${inputs.path}"},
                    },
                    {"name": "step", "subgraph": "step.yaml"},
                ],
            }
        )
    )
    graph = build_graph(tmp_path / "pipeline.yaml", functions=FUNCTIONS)
    result = await graph.run(inputs={"path": "data/"})
    assert result.status == GraphStatus.COMPLETED, result.error
    # The parent's timeout overrides the subgraph's, which keeps its retries.
    assert result.output.content == "read data/, checked 60x2"
