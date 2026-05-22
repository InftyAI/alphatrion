import asyncio
import json
import os
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

from alphatrion.runtime.contextvars import current_exp_id, current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage import runtime as storage_runtime

BEST_RESULT_PATH = "best_result_path"


async def log_artifact(
    repo_name: str,
    paths: str | list[str] | None = None,
    version: str | None = None,
    pre_save_hook: Callable[[], str | list[str] | None] | None = None,
    post_save_hook: Callable[[], None] | None = None,
) -> str | None:
    """
    Log artifacts (files) to the artifact registry.

    :param repo_name: the name of the repository to log the artifact to (required).
    :param paths: list of file paths to log.
        Support one or multiple files or a folder, multiple folders is not supported.
        If a folder is provided, all files in the folder will be logged.
        Don't support nested folders currently, only files in the first level
        of the folder will be logged.
    :param version: the version (tag) to log the files
    :param pre_save_hook: a callable function to be called before saving the artifact.
           Can return str | list[str] to override the paths parameter, or None to use paths.
           This allows dynamic file creation (e.g., checkpointing) or just side effects.
    :param post_save_hook: a callable function to be called after saving the artifact.
           Takes no arguments and returns nothing. This allows side effects after the artifact is saved,
           such as logging or cleanup.

    :return: the path of the logged artifact or None if no artifact was logged (e.g., if paths is empty).
        OCI format: {org_id}/{team_id}/{exp_id}/{repo_name}:{version}
        S3 format: {org_id}/{team_id}/{exp_id}/{repo_name}/{version}
    """

    runtime = global_runtime()
    if runtime is None:
        raise RuntimeError("Runtime is not initialized. Please call init() first.")

    if not storage_runtime.artifact_storage_enabled():
        raise RuntimeError(
            "Artifact storage is not enabled in the runtime."
            "Set ENABLE_ARTIFACT_STORAGE=true in the environment variables."
        )

    # Execute pre_save_hook if provided
    if pre_save_hook is not None:
        if not callable(pre_save_hook):
            raise ValueError("pre_save_hook must be a callable function")

        hook_result = pre_save_hook()
        # If hook returns paths, use those (override)
        if hook_result is not None:
            paths = hook_result

    # Now validate that we have paths
    if not paths:
        # TODO: replace with logging library.
        print("Warning: No paths provided for log_artifact. Nothing will be logged.")

        # We should still run the post_save_hook even if there's nothing to log,
        # because the hook might have side effects that are important (e.g., cleanup).
        if post_save_hook is not None:
            if not callable(post_save_hook):
                raise ValueError("post_save_hook must be a callable function")
            post_save_hook()
        return None

    loop = asyncio.get_running_loop()

    new_repo = f"{runtime.org_id}/{runtime.team_id}"
    exp_id = current_exp_id.get()
    if exp_id is not None:
        new_repo += f"/{exp_id}"

    path = await loop.run_in_executor(
        None,
        runtime._artifact.push,
        f"{new_repo}/{repo_name}",
        paths,
        version,
    )

    # Execute post_save_hook if provided
    if post_save_hook is not None:
        if not callable(post_save_hook):
            raise ValueError("post_save_hook must be a callable function")
        post_save_hook()

    return path


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


async def log_metrics(metrics: dict[str, float]):
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

    # Create all metrics in a single batch operation
    runtime._metadb.create_metrics(
        metrics=metrics,
        org_id=runtime.org_id,
        team_id=runtime.team_id,
        experiment_id=exp_id,
        run_id=run_id,
    )

    # track if any metric is the best metric
    should_checkpoint = False
    should_early_stop = False
    should_stop_on_target = False
    for key, value in metrics.items():
        if not isinstance(value, (int, float)):
            # TODO: replace with logging library.
            print(
                f"Warning: Metric '{key}' has non-numeric value '{value}' and will be skipped for best metric tracking."
            )
            continue

        float_value = float(value)

        # Always call the should_checkpoint_on_best first because
        # it also updates the best metric.
        should_checkpoint |= exp.should_checkpoint_on_best(
            metric_key=key, metric_value=float_value
        )

        should_early_stop |= exp.should_early_stop(
            metric_key=key, metric_value=float_value
        )
        should_stop_on_target |= exp.should_stop_on_target_metric(
            metric_key=key, metric_value=float_value
        )

    if should_checkpoint:
        path = await log_artifact(
            repo_name="ckpt",
            pre_save_hook=exp.config.checkpoint.pre_save_hook,
            post_save_hook=exp.config.checkpoint.post_save_hook,
        )

        if path is not None:
            runtime.metadb.update_run(
                run_id=run_id,
                meta={BEST_RESULT_PATH: path},
            )

    if should_early_stop or should_stop_on_target:
        exp.done()


# log_records is used to log a list of records, which is similar to log_metrics
# but for tracing the execution of the code.
# async def log_records():


async def log_dataset(
    name: str,
    data_or_path: dict[str, Any] | str | list[str],
    version: str | None = None,
) -> uuid.UUID | None:
    """
    Log dataset to the database and artifact registry.

    :param name: the name of the dataset.
    :param data_or_path: the data to be logged, it can be a dict,
                         a file path or a list of file paths.
    """
    runtime = global_runtime()

    paths = None
    tmpdir_obj = None
    try:
        if isinstance(data_or_path, dict):
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdir = tmpdir_obj.name
            file_path = os.path.join(tmpdir, name)
            with open(file_path, "w") as f:
                f.write(json.dumps(data_or_path))
            paths = [file_path]
        elif isinstance(data_or_path, (str, list)):
            paths = data_or_path if isinstance(data_or_path, list) else [data_or_path]
        else:
            raise NotImplementedError(
                f"Logging dataset of type {type(data_or_path)} is not implemented yet."
            )

        path = await log_artifact(
            repo_name="dataset",
            paths=paths,
            version=version,
        )
        if path is None:
            print(
                "Warning: log_artifact did not return a path. Dataset will not be logged."
            )
            return None

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
    finally:
        if tmpdir_obj is not None:
            tmpdir_obj.cleanup()
