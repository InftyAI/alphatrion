import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """One record in the memory history, usually the outcome of a node execution."""

    step: int = Field(description="The graph step that produced the entry.")
    node: str = Field(description="The name of the node that produced the entry.")
    type: str = Field(description="The type of the node, e.g. action or guardrail.")
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Memory:
    """
    Memory shared by all nodes of a graph. It holds two things:

    - history: an append-only log of what happened, recorded by the graph
      after each node execution, so nodes can look back at previous states.
    - values: a key-value store nodes use to pass state to each other.

    Memory can be saved to and loaded from a JSON file to share it across runs.
    """

    def __init__(
        self,
        entries: list[MemoryEntry] | None = None,
        values: dict[str, Any] | None = None,
    ):
        self._entries: list[MemoryEntry] = list(entries or [])
        self._values: dict[str, Any] = dict(values or {})

    def record(
        self, step: int, node: str, type: str, data: dict[str, Any] | None = None
    ) -> MemoryEntry:
        entry = MemoryEntry(step=step, node=node, type=type, data=data or {})
        self._entries.append(entry)
        return entry

    def history(
        self,
        node: str | None = None,
        type: str | None = None,
        last: int | None = None,
    ) -> list[MemoryEntry]:
        """Return the entries in order, optionally filtered by node or type,
        and limited to the last n matches."""
        entries = [
            e
            for e in self._entries
            if (node is None or e.node == node) and (type is None or e.type == type)
        ]
        if last is not None:
            entries = entries[-last:] if last > 0 else []
        return entries

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._values

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[MemoryEntry]:
        return iter(self._entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            # fallback=str keeps saving from failing on data that isn't JSON
            # serializable, at the cost of loading it back as strings.
            "entries": [e.model_dump(mode="json", fallback=str) for e in self._entries],
            "values": self._values,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Memory":
        return cls(
            entries=[MemoryEntry.model_validate(e) for e in data.get("entries", [])],
            values=data.get("values", {}),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), default=str, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "Memory":
        return cls.from_dict(json.loads(Path(path).read_text()))
