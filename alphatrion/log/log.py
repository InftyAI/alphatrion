import asyncio
import json
import os
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

from alphatrion.runtime.contextvars import current_exp_id, current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.snapshot.snapshot import (
    checkpoint_path,
)
from alphatrion.storage import runtime as storage_runtime

BEST_RESULT_PATH = "best_result_path"


async def log_artifact(
    paths: str | list[str],
    repo_name: str,
    version: str | None = None,
    pre_save_hook: Callable | None = None,
) -> str:
    """
    Log artifacts (files) to the artifact registry.

    :param paths: list of file paths to log.
        Support one or multiple files or a folder, multiple folders is not supported.
        If a folder is provided, all files in the folder will be logged.
        Don't support nested folders currently, only files in the first level
        of the folder will be logged.
    :param repo_name: the name of the repository to log the artifact to.
    :param version: the version (tag) to log the files
    :param pre_save_hook: a callable function to be called before saving the artifact.
           If want to save something, make sure it's under the paths.

    :return: the path of the logged artifact in the format of
    {team_id}/{repo_name}:{version}
    """

    if not paths:
        raise ValueError("no files specified to log")

    runtime = global_runtime()
    if runtime is None:
        raise RuntimeError("Runtime is not initialized. Please call init() first.")

    if not storage_runtime.artifact_storage_enabled():
        raise RuntimeError(
            "Artifact storage is not enabled in the runtime."
            "Set ENABLE_ARTIFACT_STORAGE=true in the environment variables."
        )

    if pre_save_hook is not None:
        if callable(pre_save_hook):
            pre_save_hook()
        else:
            raise ValueError("pre_save_hook must be a callable function")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, runtime._artifact.push, f"{runtime.team_id}/{repo_name}", paths, version
    )


async def log_params(params: dict):
    """
    Log parameters to the database.
    Support in Experiment level currently, should be called after starting a Experiment.

    :param params: a dict of key-value pairs to log as parameters.
    """
    exp_id = current_exp_id.get()
    if exp_id is None:
        raise RuntimeError("log_params must be called inside a Experiment.")
    runtime = global_runtime()
    # TODO: should we upload to the artifact as well?
    # current_exp_id is protect by contextvar, so it's safe to use in async
    runtime._metadb.update_experiment(
        experiment_id=exp_id,
        params=params,
    )


async def log_metrics(metrics: dict[str, float]) -> bool:
    """
    Log metrics to the database.
    Support in Run level currently, should be called after starting a Run.

    :param metrics: a dict of key-value pairs to log as metrics.
    :return: a bool indicating whether the metric is the best metric.
    """
    run_id = current_run_id.get()
    if run_id is None:
        raise RuntimeError("log_metrics must be called inside a Run.")

    runtime = global_runtime()

    exp_id = current_exp_id.get()
    if exp_id is None:
        raise RuntimeError("log_metrics must be called inside a Experiment.")

    exp = runtime.current_experiment
    if exp is None:
        raise RuntimeError(f"Experiment {exp_id} not found in the database.")

    # track if any metric is the best metric
    should_checkpoint = False
    should_early_stop = False
    should_stop_on_target = False
    is_best_metric = False
    for key, value in metrics.items():
        runtime._metadb.create_metric(
            key=key,
            value=value,
            org_id=runtime.org_id,
            team_id=runtime.team_id,
            experiment_id=exp_id,
            run_id=run_id,
        )

        # Always call the should_checkpoint_on_best first because
        # it also updates the best metric.
        should_checkpoint_tmp, is_best_metric_tmp = exp.should_checkpoint_on_best(
            metric_key=key, metric_value=value
        )
        should_checkpoint |= should_checkpoint_tmp
        is_best_metric |= is_best_metric_tmp

        should_early_stop |= exp.should_early_stop(metric_key=key, metric_value=value)
        should_stop_on_target |= exp.should_stop_on_target_metric(
            metric_key=key, metric_value=value
        )

    # TODO: refactor this with an event driven mechanism later.
    if should_checkpoint:
        path = await log_artifact(
            repo_name="ckpt",
            # If not provided, will use the default checkpoint path.
            paths=exp.config.checkpoint.path or checkpoint_path(),
            pre_save_hook=exp.config.checkpoint.pre_save_hook,
        )
        runtime.metadb.update_run(
            run_id=run_id,
            meta={BEST_RESULT_PATH: path},
        )

    if should_early_stop or should_stop_on_target:
        exp.done()

    return is_best_metric


# log_records is used to log a list of records, which is similar to log_metrics
# but for tracing the execution of the code.
# async def log_records():


async def log_dataset(
    name: str,
    data_or_path: dict[str, Any] | str | list[str],
) -> uuid.UUID | None:
    """
    Log dataset to the database and artifact registry.

    :param name: the name of the dataset.
    :param data_or_path: the data to be logged, it can be a dict,
                         a file path or a list of file paths.
    """
    runtime = global_runtime()

    if isinstance(data_or_path, dict):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            with open(name, "w") as f:
                f.write(json.dumps(data_or_path))
            file_size = os.path.getsize(name)

            path = await log_artifact(
                paths=name,
                repo_name="dataset",
            )

            id = runtime.metadb.create_dataset(
                name=name,
                org_id=runtime.org_id,
                team_id=runtime.team_id,
                user_id=runtime.user_id,
                path=path,
                experiment_id=current_exp_id.get(),
                run_id=current_run_id.get(),
                meta={"size": file_size},
            )
            return id
    elif isinstance(data_or_path, (str, list)):
        path = await log_artifact(
            paths=data_or_path,
            repo_name="dataset",
        )
        id = runtime.metadb.create_dataset(
            name=name,
            org_id=runtime.org_id,
            team_id=runtime.team_id,
            user_id=runtime.user_id,
            path=path,
            experiment_id=current_exp_id.get(),
            run_id=current_run_id.get(),
        )
        return id

    raise NotImplementedError(
        f"Logging dataset of type {type(data_or_path)} is not implemented yet."
    )
