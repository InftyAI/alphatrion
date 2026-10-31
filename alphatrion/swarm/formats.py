"""
The data formats shared by all nodes. A node declares the formats it takes
and returns, and the pipeline connects nodes whose formats match, e.g. one
returning a ModelResponse into one taking a ModelResponse. Custom formats
subclass Format.
"""

import functools
import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class Format(BaseModel):
    """The base of data formats. metadata records provenance, e.g. which
    model wrote a text."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)


class Text(Format):
    """General text, e.g. instructions or a log excerpt."""

    content: str


class Files(Format):
    """A set of files by path, e.g. the code or prompts being improved."""

    files: dict[str, str]


class ModelRequest(Format):
    """What a model is asked: a system prompt and chat messages."""

    system: str | None = None
    messages: list[dict[str, Any]] = Field(min_length=1)


class ModelResponse(Format):
    """What a model answered."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class Execution(Format):
    """A finished command, e.g. a training run or tests."""

    exit_code: int | None = Field(description="None if the run timed out.")
    stdout: str = ""
    stderr: str = ""
    duration: float = Field(description="The duration in seconds.")
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Metrics(Format):
    """Measurements, one of which is the primary score."""

    values: dict[str, float]
    primary: str
    lower_is_better: bool = False

    @model_validator(mode="after")
    def primary_is_a_value(self) -> "Metrics":
        if self.primary not in self.values:
            raise ValueError(f"The primary metric {self.primary!r} has no value")
        return self

    @property
    def score(self) -> float:
        return self.values[self.primary]


def compatible(source: Any, target: Any) -> bool:
    """Whether a value of the source format can flow into a node taking the
    target format: the same format or a subclass of it, so extending a
    format never breaks the nodes built on it. Any matches everything."""
    if source is Any or target is Any:
        return True
    if get_origin(target) in (Union, types.UnionType):
        return any(compatible(source, t) for t in get_args(target))
    if get_origin(source) in (Union, types.UnionType):
        return all(compatible(s, target) for s in get_args(source))
    if source is int and target is float:
        return True
    source_cls, target_cls = get_origin(source) or source, get_origin(target) or target
    if isinstance(source_cls, type) and isinstance(target_cls, type):
        return issubclass(source_cls, target_cls)
    return source == target


def unify(formats: list[Any]) -> Any:
    """The format of a value that can come from several paths, Any if they
    differ."""
    distinct = set(formats)
    return distinct.pop() if len(distinct) == 1 else Any


def describe(fmt: Any) -> str:
    if fmt is Any:
        return "any format"
    return getattr(fmt, "__name__", None) or str(fmt)


@functools.cache
def _adapter(fmt: Any) -> TypeAdapter | None:
    try:
        return TypeAdapter(fmt)
    except Exception:
        # Not a type pydantic can validate, e.g. a plain class.
        return None


def check_value(value: Any, fmt: Any) -> Any:
    """Validate a value against a format, returning it, coerced if needed,
    e.g. an int for a float. Raises TypeError if it doesn't match."""
    if fmt is Any:
        return value
    adapter = _adapter(fmt)
    if adapter is None:
        if isinstance(fmt, type) and not isinstance(value, fmt):
            raise TypeError(f"expected {describe(fmt)}, got {type(value).__name__}")
        return value
    try:
        return adapter.validate_python(value)
    except Exception as e:
        raise TypeError(
            f"expected {describe(fmt)}, got {type(value).__name__}: {e}"
        ) from None
