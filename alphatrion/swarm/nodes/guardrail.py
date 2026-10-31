from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import Field, PrivateAttr

from alphatrion.swarm.nodes.base import FnIO, FnRef
from alphatrion.swarm.nodes.decision import DecisionNode
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder


class GuardrailNode(DecisionNode):
    """
    Runs checks against the state, e.g. to reject an unsafe or malformed
    artifact before it is evaluated. Each check is called like an action fn,
    check(state, **params), and returns either a bool, or a
    (bool, reason) tuple.

    If all checks pass, it chooses "pass", otherwise to "fail", with the
    reasons of the failed checks as details, recorded in memory. "fail" must have an exit or a
    branch, so a failed check can't be ignored: e.g. `exit: {fail: raise}`
    fails the run.
    """

    PASS: ClassVar[str] = "pass"
    FAIL: ClassVar[str] = "fail"
    ALWAYS_IMMUTABLE: ClassVar[bool] = True
    choices: ClassVar[frozenset[str] | None] = frozenset({PASS, FAIL})

    type: Literal["guardrail"] = "guardrail"
    checks: list[FnRef] = Field(
        min_length=1, description="The checks, resolved like an action fn."
    )

    _checks: list[FnIO] = PrivateAttr()

    def _prepare(self, builder: "Builder") -> None:
        self._checks = [FnIO(builder.resolve(c), self, builder) for c in self.checks]

    @property
    def required_choices(self) -> set[str]:
        return {self.FAIL}

    async def decide(self, state: State) -> tuple[str, Any]:
        reasons = []
        for check in self._checks:
            result = await check(state)
            passed, reason = result if isinstance(result, tuple) else (result, None)
            if not passed:
                reasons.append(reason or getattr(check.fn, "__name__", repr(check.fn)))

        return (self.FAIL if reasons else self.PASS), reasons
