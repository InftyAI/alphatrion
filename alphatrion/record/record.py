from alphatrion.runtime.runtime import global_runtime
from alphatrion.trial.trial import current_trial_id


def log_artifact(
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

    exp_obj = runtime._metadb.get_exp(exp.id)
    if exp_obj is None:
        raise RuntimeError(f"Experiment {exp.id} not found in the database.")

    runtime._artifact.push(repo_name=str(exp_obj.uuid), paths=paths, version=version)


# log_params is used to save a set of parameters, which is a dict of key-value pairs.
# should be called after starting a trial.
def log_params(params: dict):
    runtime = global_runtime()
    # TODO: should we upload to the artifact as well?
    # current_trial_id is protect by contextvar, so it's safe to use in async
    runtime._metadb.update_trial(
        trial_id=current_trial_id.get(),
        params=params,
    )


# log_metrics is used to log a set of metrics at once.
# metric key must be string, value must be float
def log_metrics(metrics: dict[str, float]):
    runtime = global_runtime()
    exp = runtime.current_exp

    trial_id = current_trial_id.get()
    trial = exp.get_trial(id=trial_id)
    if trial is None:
        raise RuntimeError(f"Trial {trial_id} not found in the database.")

    step = trial.increment_step()
    for key, value in metrics.items():
        runtime._metadb.create_metric(
            key=key,
            value=value,
            trial_id=trial.id,
            step=step,
        )
