import asyncio
import uuid

from alphatrion.artifact.artifact import ARTIFACT_TYPE_S3
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
    Load checkpoint from artifact registry, the path is expected to be in the format of
    "org_id/team_id/exp_id/ckpt/".

    :param id: the id of the experiment.
    :param version: the version of the checkpoint to load, default is "latest".
        If version is "latest", it will load the latest version (for oci backend) or
        the file with the latest timestamp (for s3 backend).
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

    # We only need to do this for s3 backend, because for oci backend,
    # the version is the tag and "latest" tag will always point to the latest version.
    if version == "latest" and artifact.storage_type == ARTIFACT_TYPE_S3:
        versions = artifact.list_versions(repo_name)
        if versions is None or len(versions) == 0:
            return []

        version = versions[0]  # Assuming versions are sorted by time, newest first

    result = await asyncio.get_running_loop().run_in_executor(
        None, artifact.pull, repo_name, version, output_dir
    )

    return result
