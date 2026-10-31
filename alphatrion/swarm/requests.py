from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from alphatrion.swarm.formats import ModelRequest, ModelResponse


class RequestRecord(BaseModel):
    """One model request: what was asked, of which model, and what it
    answered, or why it failed."""

    number: int = Field(description="The request's number, in order, from 1.")
    node: str = Field(description="The node that sent it.")
    branch: str | None = Field(default=None, description="Its parallel branch.")
    iteration: dict[str, int] = Field(
        default_factory=dict, description="Each loop's iteration when it was sent."
    )
    model: str
    request: ModelRequest
    response: ModelResponse | None = None
    error: str | None = Field(default=None, description="Why it failed, if it did.")
    duration: float = Field(description="In seconds.")
    artifact_id: str | None = Field(
        default=None, description="The current artifact when it was sent."
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Requests:
    """
    Every model request a run sent, in order, with its full content, for the
    run itself, e.g. to check that a router's weights pick the models they
    should, or to link an artifact to the request it came from. Parallel
    branches share it. It's kept in memory: to keep requests, trace them,
    with alphatrion.swarm.tracing.
    """

    def __init__(self) -> None:
        self._records: list[RequestRecord] = []

    def add(self, **fields: Any) -> RequestRecord:
        record = RequestRecord(number=len(self._records) + 1, **fields)
        self._records.append(record)
        return record

    def get(self, number: int) -> RequestRecord:
        return self._records[number - 1]

    def counts(self) -> Counter:
        """How many requests each model was sent."""
        return Counter(r.model for r in self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[RequestRecord]:
        return iter(self._records)
