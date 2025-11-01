import time
import functools
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter


# ===== 1️⃣ 初始化 OpenTelemetry 追踪环境 =====
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# ===== 2️⃣ 初始化 OpenAI 客户端（可替换为任意 key） =====
import os
client = OpenAI(
    base_url="https://api.deepinfra.com/v1",
    api_key=os.environ.get("DEEPINFRA_API_KEY", "dummy-key"),
    )


# ===== 3️⃣ 自定义本地 @task 和 @workflow 装饰器 =====
def task(name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_as_current_span(span_name):
                start = time.time()
                result = func(*args, **kwargs)
                end = time.time()
                print(f"🧩 Task [{span_name}] took {end - start:.3f}s")
                return result
        return wrapper
    return decorator


def workflow(name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wf_name = name or func.__name__
            with tracer.start_as_current_span(wf_name):
                print(f"\n🚀 Starting workflow: {wf_name}")
                result = func(*args, **kwargs)
                print(f"✅ Workflow [{wf_name}] finished\n")
                return result
        return wrapper
    return decorator


# ===== 4️⃣ 定义任务 =====
@task(name="joke_creation")
def create_joke():
    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3.2-Exp",
        messages=[{"role": "user", "content": "Tell me a joke about OpenTelemetry"}],
    )
    return completion.choices[0].message.content


@task(name="signature_generation")
def generate_signature(joke: str):
    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3.2-Exp",
        messages=[{"role": "user", "content": "add a signature to the joke:\n\n" + joke}],
    )
    return completion.choices[0].message.content


@task(name="joke_translation")
def translate_joke_to_pirate(joke: str):
    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3.2-Exp",
        messages=[{"role": "user", "content": f"Translate this to pirate English:\n\n{joke}"}],
    )
    return completion.choices[0].message.content


# ===== 5️⃣ 定义工作流 =====
@workflow(name="pirate_joke_generator")
def joke_workflow():
    eng_joke = create_joke()
    pirate_joke = translate_joke_to_pirate(eng_joke)
    signature = generate_signature(pirate_joke)
    print("\n--- Final Joke ---")
    print(pirate_joke + "\n\n" + signature)


# ===== 6️⃣ 执行 =====
if __name__ == "__main__":
    joke_workflow()
