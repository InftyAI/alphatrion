"""
The node functions of the EPLB pipeline, after ADRS's eplb example
(https://github.com/UCB-ADRS/ADRS/tree/main/openevolve/examples/ADRS/eplb):
a model edits the evolve block of rebalance_experts(), and ADRS's evaluator
scores it on the expert-load trace.

upstream/initial_program.py and upstream/evaluator.py are ADRS's, unchanged,
so the scores are the same as theirs. The evaluator runs in the pipeline's
eval runtime, where the trace is mounted at /data and ADRS's code at
/upstream.
"""

import json
import re
from pathlib import Path

from alphatrion.swarm import (
    Choice,
    Files,
    Metrics,
    ModelRequest,
    ModelResponse,
    ScoreMode,
    State,
)

HERE = Path(__file__).parent
PROGRAM = "program.py"
START, END = "# EVOLVE-BLOCK-START", "# EVOLVE-BLOCK-END"
METRICS = ("combined_score", "balancedness_score", "speed_score")
# ADRS's evaluator timeout, after which a program scores 0.
EVALUATOR_TIMEOUT = 60
# Runs ADRS's evaluate(), from the directory in argv[1], on the program in
# argv[2], and prints its result as the last line.
RUNNER = (
    "import json, sys; sys.path.insert(0, sys.argv[1]); import evaluator; "
    "print('RESULT ' + json.dumps(evaluator.evaluate(sys.argv[2])))"
)
EDIT = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.S)


def seed(state: State) -> Files:
    """ADRS's initial program, as the root artifact. A continued experiment
    already has it, and starts from it again."""
    if state.tree.root is not None:
        return state.checkout(state.tree.root.id).content
    program = Files(files={PROGRAM: (HERE / "upstream/initial_program.py").read_text()})
    state.commit(program, metadata={"description": "initial program"})
    return program


def prompt(state: State, instructions: str) -> ModelRequest:
    """Ask for one improvement of the best program so far, with how every
    program so far did."""
    best = state.checkout(state.tree.best(ScoreMode.MAX).id).content
    return ModelRequest(
        system=Path(instructions).read_text(),
        messages=[
            {
                "role": "user",
                "content": (
                    f"The best program so far:\n\n```python\n{best.files[PROGRAM]}```"
                    f"\n\nEvery program so far:\n\n{history(state)}\n\n"
                    "Propose the next improvement."
                ),
            }
        ],
    )


def edit(state: State, reply: ModelResponse) -> Files:
    """Apply the reply's edits to the current program, as a new artifact. A
    reply whose edits don't each match the program exactly once is skipped."""
    code = state.current.content.files[PROGRAM]
    edits = EDIT.findall(reply.text)
    if not edits or any(code.count(search) != 1 for search, _ in edits):
        raise Choice("skip", "the reply has no edits matching the program exactly once")
    for search, replace in edits:
        code = code.replace(search, replace, 1)
    match = re.search(r"^Description:\s*(.+)$", reply.text, re.M)
    program = Files(files={PROGRAM: code})
    state.commit(
        program,
        metadata={
            "description": match.group(1).strip() if match else "no description",
            # Which request and model it came from, e.g. to check the
            # router's weights against how each model's programs did.
            "model": reply.model,
            "request": reply.metadata.get("request"),
        },
    )
    return program


def in_evolve_block(state: State, program: Files) -> tuple[bool, str]:
    """The guard's check: only the evolve block changed from the seed."""
    seed = state.tree.root.content.files[PROGRAM]
    code = program.files[PROGRAM]
    return outside(code) == outside(
        seed
    ), "the edits change the program outside the evolve block"


async def measure(state: State, program: Files) -> Metrics:
    """The evaluator: ADRS's combined score, the mean of the balancedness and
    the speed, both higher is better. As in ADRS, a program that raises or
    runs past the timeout scores 0, while an evaluator that doesn't run at
    all, e.g. without the trace, fails the node."""
    await state.runtime.write(f"/work/{PROGRAM}", program.files[PROGRAM])
    run = await state.runtime.exec(
        "python",
        ["-c", RUNNER, "/upstream", f"/work/{PROGRAM}"],
        cwd="/data",
        timeout=EVALUATOR_TIMEOUT,
    )
    match = re.search(r"^RESULT (.*)$", run.stdout, re.M)
    if not run.timed_out and match is None:
        # ADRS's evaluator didn't run, e.g. the trace is missing: a mistake
        # in the setup, not the program's fault.
        raise RuntimeError(f"ADRS's evaluator failed:\n{run.stderr[-2000:]}")
    scores = json.loads(match.group(1)) if run.succeeded and match else {}
    return Metrics(
        values={key: float(scores.get(key, 0.0)) for key in METRICS},
        primary="combined_score",
    )


def history(state: State) -> str:
    """Every program so far, from the tree: its score, or that the guard
    rejected it, and its description."""
    lines = []
    for artifact in state.tree:
        score = "rejected" if artifact.score is None else f"{artifact.score:.4f}"
        lines.append(f"- {score}: {artifact.metadata.get('description', '')}")
    return "\n".join(lines)


def outside(code: str) -> tuple[str, str]:
    """The code before and after the evolve block."""
    return code.partition(START)[0], code.rpartition(END)[2]


FUNCTIONS = {fn.__name__: fn for fn in (seed, prompt, edit, in_evolve_block, measure)}
