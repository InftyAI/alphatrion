# ruff: noqa: E501


import pytest
from openai import OpenAI

import alphatrion as alpha
from alphatrion.run.run import current_run_id

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="",
)


@alpha.task()
def create_joke():
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[{"role": "user", "content": "Tell me a joke about opentelemetry"}],
    )
    return completion.choices[0].message.content


@alpha.task()
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


@alpha.task()
def print_joke(res: str):
    print("Joke:", res)


@alpha.workflow()
async def joke_workflow():
    assert current_run_id.get() is not None

    eng_joke = create_joke()
    translated_joke = translate_joke_to_pirate(eng_joke)
    print_joke(translated_joke)


@pytest.mark.asyncio
async def test_workflow():
    async with alpha.CraftExperiment.setup("demo_joke_workflow") as exp:
        async with exp.start_trial("demo_joke_trial") as trial:
            task = trial.start_run(lambda: joke_workflow())
            await task.wait()

        assert exp.get_trial(trial.id) is None
