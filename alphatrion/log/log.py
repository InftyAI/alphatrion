from alphatrion.run.run import current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.trial.trial import current_trial_id
from alphatrion.utils import time as utime


async def log_artifact(
    paths: str | list[str],
    version: str = "latest",
):
    """
    Log artifacts (files) to the artifact registry.

    :param exp_id: the experiment ID
    :param paths: list of file paths to log.
        Support one or multiple files or a folder.
        If a folder is provided, all files in the folder will be logged.
        Don't support nested folders currently, only files in the first level
        of the folder will be logged.
    :param version: the version (tag) to log the files
    """

    if not paths:
        raise ValueError("no files specified to log")

    runtime = global_runtime()
    if runtime is None:
        raise RuntimeError("Runtime is not initialized. Please call init() first.")

    # We use experiment ID as the repo name rather than the experiment name,
    # because experiment name is not unique
    exp = runtime.current_exp
    if exp is None:
        raise RuntimeError("No running experiment found in the current context.")

    runtime._artifact.push(repo_name=str(exp.id), paths=paths, version=version)


# log_params is used to save a set of parameters, which is a dict of key-value pairs.
# should be called after starting a trial.
async def log_params(params: dict):
    trial_id = current_trial_id.get()
    if trial_id is None:
        raise RuntimeError("log_params must be called inside a Trial.")
    runtime = global_runtime()
    # TODO: should we upload to the artifact as well?
    # current_trial_id is protect by contextvar, so it's safe to use in async
    runtime._metadb.update_trial(
        trial_id=trial_id,
        params=params,
    )


# log_metrics is used to log a set of metrics at once,
# metric key must be string, value must be float.
# If save_on_best is enabled in the trial config, and the metric is the best metric
# so far, the trial will checkpoint the current data.
#
# Note: log_metrics can only be called inside a Run, because it needs a run_id.
async def log_metrics(metrics: dict[str, float]):
    run_id = current_run_id.get()
    if run_id is None:
        raise RuntimeError("log_metrics must be called inside a Run.")

    runtime = global_runtime()
    exp = runtime.current_exp

    trial_id = current_trial_id.get()
    if trial_id is None:
        raise RuntimeError("log_metrics must be called inside a Trial.")

    trial = exp.get_trial(id=trial_id)
    if trial is None:
        raise RuntimeError(f"Trial {trial_id} not found in the database.")

    # track if any metric is the best metric
    should_checkpoint = False
    should_early_stop = False
    step = trial.increment_step()
    for key, value in metrics.items():
        runtime._metadb.create_metric(
            key=key,
            value=value,
            project_id=runtime._project_id,
            trial_id=trial_id,
            run_id=run_id,
            step=step,
        )

        # TODO: should we save the checkpoint path for the best metric?
        # Always call the should_checkpoint_on_best first because
        # it also updates the best metric.
        should_checkpoint |= trial.should_checkpoint_on_best(
            metric_key=key, metric_value=value
        )
        should_early_stop |= trial.should_early_stop(metric_key=key, metric_value=value)

    if should_checkpoint:
        await log_artifact(
            paths=trial.config().checkpoint.path,
            version=utime.now_2_hash(),
        )

    if should_early_stop:
        trial.cancel()
