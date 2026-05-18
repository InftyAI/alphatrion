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


async def load_checkpoint(
    id: str | uuid.UUID,
    version: str = "latest",
    type: str = "experiment",
    output_dir: str | None = None,
) -> list[str]:
    """
    Load checkpoint from artifact registry.

    :param id: the id of the experiment.
    :param version: the version of the checkpoint to load, default is "latest".
        For oci backend, version is the tag of the artifact.
        For s3 backend, version is the name of the file to load.
            If version is "latest", the most recently modified file will be loaded.
    :param type: the type of the checkpoint, can be "experiment" or "agent", default is "experiment".
    :param output_dir: the directory to which the checkpoint will be loaded.
    """
    runtime = global_runtime()

    if isinstance(id, str):
        id = uuid.UUID(id)

    artifact = runtime.artifact
    if artifact is None:
        raise RuntimeError("Artifact storage is not initialized in the runtime.")

    repo_name = f"{runtime.org_id}/{runtime.team_id}/{id}/ckpt"

    versions = artifact.list_versions(repo_name)
    if versions is None or len(versions) == 0:
        return []

    if version == "latest":
        version = versions[0]  # Assuming versions are sorted by time, newest first

    result = await asyncio.get_running_loop().run_in_executor(
        None, artifact.pull, repo_name, version, output_dir
    )

    return result
