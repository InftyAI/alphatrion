import asyncio
import os
from collections.abc import Callable
from typing import Any

from alphatrion.experiment.base import current_exp_id
from alphatrion.run.run import current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.snapshot.snapshot import (
    RecordKind,
    build_run_record,
    checkpoint_path,
    snapshot_path,
)

BEST_RESULT_PATH = "best_result_path"
RECORD_PATH = "record_path"


async def log_artifact(
    paths: str | list[str],
    version: str | None = None,
    repo_name: str | None = None,
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
    {team_id}/{project_id}:{version}
    """

    if not paths:
        raise ValueError("no files specified to log")

    runtime = global_runtime()
    if runtime is None:
        raise RuntimeError("Runtime is not initialized. Please call init() first.")

    if not runtime.artifact_storage_enabled():
        raise RuntimeError(
            "Artifact storage is not enabled in the runtime."
            "Set ENABLE_ARTIFACT_STORAGE=true in the environment variables."
        )

    if pre_save_hook is not None:
        if callable(pre_save_hook):
            pre_save_hook()
        else:
            raise ValueError("pre_save_hook must be a callable function")

    # We use project ID as the repo name rather than the project name,
    # because project name is not unique and might change over time.
    proj = runtime.current_proj
    if proj is None:
        raise RuntimeError("No running project found in the current context.")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, runtime._artifact.push, repo_name or str(proj.id), paths, version
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
    proj = runtime.current_proj

    exp_id = current_exp_id.get()
    if exp_id is None:
        raise RuntimeError("log_metrics must be called inside a Experiment.")

    exp = proj.get_experiment(id=exp_id)
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
            project_id=proj.id,
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
            repo_name=f"{str(proj.id)}/ckpt",
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


# log_record is used to log the record of a run/experiment/project.
# For example, you want to save the code snippet. It will be stored
# in the object storage as a JSON file if object storage is enabled.
async def log_record(
    content: dict[str, Any],
    kind: RecordKind = RecordKind.RUN,
):
    save_path = ""
    record = None

    if kind == RecordKind.RUN:
        save_path = snapshot_path()
        record = build_run_record(content=content)
    else:
        raise NotImplementedError(
            f"Logging record of kind {record.kind} is not implemented yet."
        )

    if os.path.exists(save_path) is False:
        os.makedirs(save_path, exist_ok=True)

    # TODO: Will this leads to increasing memory usage, especially for kubernetes?
    with open(os.path.join(save_path, "record.json"), "w") as f:
        f.write(record.model_dump_json())

    runtime = global_runtime()

    # If not enabled, only save to local disk.
    if runtime.artifact_storage_enabled():
        path = await log_artifact(
            paths=os.path.join(save_path, "record.json"),
            repo_name=f"{str(runtime.current_proj.id)}/record",
        )
        runtime.metadb.update_run(
            run_id=current_run_id.get(),
            meta={RECORD_PATH: path},
        )
