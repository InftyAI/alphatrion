import os
from openai import OpenAI
from traceloop.sdk.decorators import workflow, task
from traceloop.sdk import Traceloop
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

client = OpenAI(
    base_url="https://api.deepinfra.com/v1",
    api_key=os.environ.get("DEEPINFRA_API_KEY", "dummy-key"),
    )


@task(name="joke_creation")
def create_joke():
    completion = client.chat.completions.create( model="deepseek-ai/DeepSeek-V3.2-Exp", messages=[{"role": "user", "content": "Tell me a joke about opentelemetry"}], )
    return completion.choices[0].message.content

@task(name="joke_translation")
def translate_joke_to_pirate(joke: str):
    completion = client.chat.completions.create( model="deepseek-ai/DeepSeek-V3.2-Exp", messages=[{"role": "user", "content": f"Translate the below joke to pirate-like english:\n\n{joke}"}], )
    return completion.choices[0].message.content

@task(name="signature_generation")
def generate_signature(joke: str):
    completion = client.chat.completions.create( model="deepseek-ai/DeepSeek-V3.2-Exp", messages=[{"role": "user", "content": "add a signature to the joke:\n\n" + joke}], )
    return completion.choices[0].message.content

@workflow(name="pirate_joke_generator")
def joke_workflow():
    eng_joke = create_joke()
    pirate_joke = translate_joke_to_pirate(eng_joke)
    signature = generate_signature(pirate_joke)
    # print("pirate_joke: \n" + pirate_joke + "\n\n'signature': \n" + signature)

if __name__ == "__main__":
    Traceloop.init(
        exporter=ConsoleSpanExporter(),
        disable_batch=True,
    )
    joke_workflow()
