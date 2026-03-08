import asyncio
import json
import os
import tempfile
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


# log_params is used to save a set of parameters, which is a dict of key-value pairs.
# should be called after starting a Experiment.
async def log_params(params: dict):
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


# log_metrics is used to log a set of metrics at once,
# metric key must be string, value must be float.
# If save_on_best is enabled in the experiment config, and the metric is the best metric
# so far, the experiment will checkpoint the current data.
#
# Note: log_metrics can only be called inside a Run, because it needs a run_id.
# Return bool indicates whether the metric is the best metric.
async def log_metrics(metrics: dict[str, float]) -> bool:
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
            team_id=runtime._team_id,
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
            paths=exp.config().checkpoint.path or checkpoint_path(),
            pre_save_hook=exp.config().checkpoint.pre_save_hook,
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
):
    """
    Log dataset to the database and artifact registry.

    :param name: the name of the dataset.
    :param data_or_path: the data to be logged, currently support dict only,
                 will support more types in the future.
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

            runtime.metadb.create_dataset(
                name=name,
                team_id=runtime.team_id,
                user_id=runtime.user_id,
                path=path,
                experiment_id=current_exp_id.get(),
                run_id=current_run_id.get(),
                meta={"size": file_size},
            )
            return
    elif isinstance(data_or_path, (str, list)):
        path = await log_artifact(
            paths=data_or_path,
            repo_name="dataset",
        )
        runtime.metadb.create_dataset(
            name=name,
            team_id=runtime.team_id,
            user_id=runtime.user_id,
            path=path,
            experiment_id=current_exp_id.get(),
            run_id=current_run_id.get(),
        )
        return

    raise NotImplementedError(
        f"Logging dataset of type {type(data_or_path)} is not implemented yet."
    )
