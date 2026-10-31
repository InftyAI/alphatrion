import pytest
import yaml

from alphatrion.swarm import ActionNode, Choice, GraphStatus, Text, build_graph


def draft(state) -> Text:
    return Text(content="draft")


def shout(state, text: Text, suffix: str) -> Text:
    return Text(content=text.content.upper() + suffix)


def too_long(state, text: Text, limit: int) -> Text:
    if len(text.content) > limit:
        raise Choice("skip", f"longer than {limit}")
    return text


FUNCTIONS = {fn.__name__: fn for fn in (draft, shout, too_long)}


def build(pipeline: str):
    return build_graph(yaml.safe_load(pipeline), functions=FUNCTIONS)


DRAFT = "{name: draft, type: action, fn: draft}"


@pytest.mark.asyncio
async def test_a_function_gets_its_node_s_params():
    result = await build(
        f"""
        nodes:
          - {DRAFT}
          - name: shout
            type: action
            fn: shout
            params: {{text: "${{nodes.draft.output}}", suffix: "!"}}
        """
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.output == Text(content="DRAFT!")


@pytest.mark.asyncio
async def test_a_chosen_choice_has_no_output():
    result = await build(
        f"""
        nodes:
          - {DRAFT}
          - name: check
            type: action
            fn: too_long
            params: {{text: "${{nodes.draft.output}}", limit: 3}}
            exit: {{skip: end}}
        """
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    entry = result.state.memory.history(node="check")[-1]
    assert (entry.data["choice"], entry.data["details"]) == ("skip", "longer than 3")
    assert entry.data["output"] is None
    # The run's output is its last one, draft's.
    assert result.output == Text(content="draft")


def test_formats():
    node = ActionNode(
        name="f", fn=too_long, params={"text": {"content": "x"}, "limit": 3}
    )
    build_graph({"nodes": [node]})
    # Raising Choice chooses a choice, so the output is only ever a Text.
    assert node.output_type() is Text


def test_params_must_be_given_and_taken():
    with pytest.raises(ValueError, match="function shout takes 'text', which the node"):
        build(
            f'nodes: [{DRAFT}, {{name: f, type: action, fn: shout, params: {{suffix: "!"}}}}]'
        )
    with pytest.raises(ValueError, match="params it doesn't take: sufix"):
        build(
            f"nodes: [{DRAFT}, {{name: f, type: action, fn: shout, params: "
            '{text: "${nodes.draft.output}", suffix: "!", sufix: "?"}}]'
        )


def test_param_types_are_checked_when_built():
    with pytest.raises(ValueError, match="Node f param limit: expected int"):
        build(
            f'nodes: [{DRAFT}, {{name: f, type: action, fn: too_long, params: {{text: "${{nodes.draft.output}}", limit: three}}}}]'
        )


@pytest.mark.asyncio
async def test_input_types_are_checked_when_called():
    graph = build(
        f"""
        inputs: [n]
        nodes:
          - {DRAFT}
          - name: f
            type: action
            fn: too_long
            params: {{text: "${{nodes.draft.output}}", limit: "${{inputs.n}}"}}
        """
    )
    result = await graph.run(inputs={"n": "three"})
    assert result.status == GraphStatus.FAILED
    assert "Node f param limit: expected int" in result.error
    # A value of the right kind is coerced, e.g. "30" for an int.
    assert (await graph.run(inputs={"n": "30"})).status == GraphStatus.COMPLETED


def test_describe():
    graph = build(
        f"""
        inputs: [n]
        nodes:
          - {DRAFT}
          - name: improve
            type: loop
            max_iters: 3
            nodes:
              - name: check
                type: action
                fn: too_long
                params: {{text: "${{nodes.draft.output}}", limit: "${{inputs.n}}"}}
                timeout: 5s
                retries: 1
                exit: {{skip: continue}}
              - name: shout
                type: action
                fn: shout
                params: {{text: "${{nodes.check.output}}", suffix: "!"}}
        """
    )
    assert graph.describe().splitlines() == [
        "draft    -> Text  action",
        "improve  -> Text  loop  max_iters: 3",
        "  check  -> Text  action  params: text=${nodes.draft.output}, limit=${inputs.n}  timeout: 5s  retries: 1  choices: skip -> continue",
        "  shout  -> Text  action  params: text=${nodes.check.output}, suffix=!",
    ]


@pytest.mark.asyncio
async def test_a_raised_choice_is_an_outcome_never_retried():
    calls = []

    def skip(state):
        calls.append(1)
        raise Choice("skip", "nothing to do")

    graph = build_graph(
        {
            "nodes": [
                {
                    "name": "f",
                    "type": "action",
                    "fn": skip,
                    "retries": 3,
                    "exit": {"skip": "end"},
                }
            ]
        }
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert calls == [1]
    assert result.state.memory.history(node="f")[-1].data["details"] == "nothing to do"
