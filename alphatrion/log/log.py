import asyncio
from collections.abc import Callable

from alphatrion.experiment.base import current_exp_id
from alphatrion.run.run import current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.utils import time as utime

BEST_RESULT_PATH = "best_result_path"


async def log_artifact(
    paths: str | list[str],
    version: str = "latest",
    pre_save_hook: Callable | None = None,
) -> str:
    """
    Log artifacts (files) to the artifact registry.

    :param paths: list of file paths to log.
        Support one or multiple files or a folder.
        If a folder is provided, all files in the folder will be logged.
        Don't support nested folders currently, only files in the first level
        of the folder will be logged.
    :param version: the version (tag) to log the files
    :param pre_save_hook: a callable function to be called before saving the artifact.

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
        None, runtime._artifact.push, str(proj.id), paths, version
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
async def log_metrics(metrics: dict[str, float]):
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
    for key, value in metrics.items():
        runtime._metadb.create_metric(
            key=key,
            value=value,
            team_id=runtime._team_id,
            project_id=proj.id,
            experiment_id=exp_id,
            run_id=run_id,
        )

        # TODO: should we save the checkpoint path for the best metric?
        # Always call the should_checkpoint_on_best first because
        # it also updates the best metric.
        should_checkpoint |= exp.should_checkpoint_on_best(
            metric_key=key, metric_value=value
        )
        should_early_stop |= exp.should_early_stop(metric_key=key, metric_value=value)
        should_stop_on_target |= exp.should_stop_on_target_metric(
            metric_key=key, metric_value=value
        )

    if should_checkpoint:
        path = await log_artifact(
            paths=exp.config().checkpoint.path,
            version=utime.now_2_hash(),
            pre_save_hook=exp.config().checkpoint.pre_save_hook,
        )
        runtime._metadb.update_run(
            run_id=run_id,
            meta={BEST_RESULT_PATH: path},
        )

    if should_early_stop or should_stop_on_target:
        exp.done()
