# ruff: noqa: E501


import asyncio
import os

import pytest
from openai import OpenAI

from alphatrion import envs, experiment, project, tracing
from alphatrion.run.run import current_run_id

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="",
)


@tracing.task()
def create_joke():
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[{"role": "user", "content": "Tell me a joke about opentelemetry"}],
    )
    return completion.choices[0].message.content


@tracing.task()
def translate_joke_to_pirate(joke: str):
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[
            {
                "role": "user",
                "content": f"Translate the below joke to pirate-like english:\n\n{joke}",
            }
        ],
    )
    return completion.choices[0].message.content


@tracing.task()
def print_joke(res: str):
    print("Joke:", res)


@tracing.workflow()
async def joke_workflow():
    assert current_run_id.get() is not None

    eng_joke = create_joke()
    translated_joke = translate_joke_to_pirate(eng_joke)
    print_joke(translated_joke)


@pytest.mark.asyncio
async def test_workflow():
    async with project.Project.setup("demo_joke_workflow") as proj:
        async with experiment.CraftExperiment.start("demo_joke_experiment") as exp:
            run = exp.run(lambda: joke_workflow())
            await run.wait()

            # Wait for spans to be exported (they're batched)
            await asyncio.sleep(2)
            from alphatrion.storage.tracestore import TraceStore

            trace_store = TraceStore(
                host=os.getenv(envs.CLICKHOUSE_URL, "localhost:8123"),
                database=os.getenv(envs.CLICKHOUSE_DATABASE, "alphatrion_traces"),
                username=os.getenv(envs.CLICKHOUSE_USERNAME, "alphatrion"),
                password=os.getenv(envs.CLICKHOUSE_PASSWORD, "alphatr1on"),
                init_tables=os.getenv(envs.CLICKHOUSE_INIT_TABLES, "false").lower()
                == "true",
            )

            try:
                # Get traces for this run
                print(f"Querying for run_id: {run.id}")
                traces = trace_store.get_traces_by_run_id(run.id)
                print(f"Found {len(traces)} traces")

                # Verify we have traces
                assert len(traces) > 0, (
                    f"Expected traces to be stored in ClickHouse for run_id {run.id}"
                )

                # Verify trace structure
                for trace in traces:
                    assert "TraceId" in trace
                    assert "SpanId" in trace
                    assert "SpanName" in trace
                    assert "SpanAttributes" in trace

                    # Verify core identifiers are in dedicated columns
                    assert trace["RunId"] == str(run.id)
                    assert trace["ProjectId"] == str(proj.id)
                    assert trace["ExperimentId"] == str(exp.id)
                    assert "TeamId" in trace

                    # Verify run_id is also in attributes for backward compatibility
                    assert trace["SpanAttributes"].get("run_id") == str(run.id)

                print(f"✓ Verified {len(traces)} traces stored in ClickHouse")
            finally:
                trace_store.close()

        assert proj.get_experiment(exp.id) is None
