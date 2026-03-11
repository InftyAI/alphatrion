import asyncio
import uuid

from alphatrion.runtime.runtime import global_runtime


async def load_dataset(id: str | uuid.UUID, output_dir: str | None = None) -> list[str]:
    """
    Load dataset from artifact registry.

    :param id: the id of the dataset.
    :param output_dir: the directory to which the dataset will be loaded.
    """
    runtime = global_runtime()

    if isinstance(id, str):
        id = uuid.UUID(id)

    dataset = runtime.metadb.get_dataset(dataset_id=id)

    repo_name, version = dataset.path.split(":")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, runtime._artifact.pull, repo_name, version, output_dir
    )

    return result
