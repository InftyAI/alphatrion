# ruff: noqa: E501

from openai import OpenAI

from alphatrion.tracing.tracing import task, workflow

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="",
)


@task(name="joke_creation")
def create_joke():
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[{"role": "user", "content": "Tell me a joke about opentelemetry"}],
    )
    return completion.choices[0].message.content


@task(name="joke_translation")
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


@task(name="signature_generation")
def generate_signature(joke: str):
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[
            {"role": "user", "content": "add a signature to the joke:\n\n" + joke}
        ],
    )
    return completion.choices[0].message.content


@workflow(name="pirate_joke_generator")
def joke_workflow():
    eng_joke = create_joke()
    pirate_joke = translate_joke_to_pirate(eng_joke)
    signature = generate_signature(pirate_joke)
    return pirate_joke, signature


def test_workflow():
    pirate_joke, signature = joke_workflow()
    assert pirate_joke is not None
    assert signature is not None


if __name__ == "__main__":
    test_workflow()
