from collections import ChainMap
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

# The inputs of the current run, e.g. a data directory, given to graph.run().
# They belong to the run rather than the state, which outlives it, and
# reach node functions as params. Parallel branches see them too, since
# asyncio tasks copy the context.
_inputs: ContextVar[dict[str, Any] | None] = ContextVar("inputs", default=None)


def current_inputs() -> dict[str, Any]:
    return _inputs.get() or {}


@contextmanager
def run_inputs(inputs: dict[str, Any] | None) -> Iterator[dict[str, Any]]:
    """Set the inputs of a run for its duration. A nested run, e.g. a loop
    body, passes None and keeps the inputs of the run it's part of."""
    if inputs is None:
        yield current_inputs()
        return
    token = _inputs.set({**current_inputs(), **inputs})
    try:
        yield _inputs.get()
    finally:
        _inputs.reset(token)


# The runtime of the node attempt running, which node functions reach as
# state.runtime. Nested nodes, e.g. in a loop with a runtime, share it.
_runtime: ContextVar[Any] = ContextVar("runtime", default=None)


def current_runtime() -> Any:
    return _runtime.get()


@contextmanager
def using_runtime(runtime: Any) -> Iterator[None]:
    token = _runtime.set(runtime)
    try:
        yield
    finally:
        _runtime.reset(token)


# The outputs of the nodes that have run, by name, which nodes reference as
# ${nodes.name.output}. Each graph run has a scope of its own over the one it
# is part of, so a loop iteration or a parallel branch sees the outputs
# before it, and its own, but no other's.
_outputs: ContextVar[ChainMap | None] = ContextVar("outputs", default=None)


def current_outputs() -> ChainMap:
    return _outputs.get() or ChainMap()


@contextmanager
def output_scope() -> Iterator[ChainMap]:
    scope = current_outputs().new_child()
    token = _outputs.set(scope)
    try:
        yield scope
    finally:
        _outputs.reset(token)


# The store keeping the run, if any, given to graph.run(store=...). Nested
# runs record into it too.
_store: ContextVar[Any] = ContextVar("store", default=None)


def current_store() -> Any:
    return _store.get()


@contextmanager
def using_store(store: Any) -> Iterator[None]:
    token = _store.set(store)
    try:
        yield
    finally:
        _store.reset(token)


# The iteration each loop running is at, by loop, e.g. {"research": 4}, so
# what a node records says where in the run it happened. Nested loops add
# theirs.
_iterations: ContextVar[dict[str, int] | None] = ContextVar("iterations", default=None)


def current_iterations() -> dict[str, int]:
    return dict(_iterations.get() or {})


@contextmanager
def in_iteration(loop: str, iteration: int) -> Iterator[None]:
    token = _iterations.set({**current_iterations(), loop: iteration})
    try:
        yield
    finally:
        _iterations.reset(token)
