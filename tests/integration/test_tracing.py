# ruff: noqa: E501


from openai import OpenAI

from alphatrion import tracing
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
