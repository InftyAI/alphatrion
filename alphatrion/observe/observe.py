from alphatrion.runtime.runtime import global_runtime


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

    exp_id = runtime._current_exp_id
    if exp_id is None:
        raise RuntimeError("No running experiment found.")

    exp = runtime._metadb.get_exp(exp_id=exp_id)
    if exp is None:
        raise ValueError(f"Experiment with id {exp_id} does not exist.")

    runtime._artifact.push(experiment_name=exp.name, paths=paths, version=version)


# def log_params(exp_id: int, params: dict):
#     runtime = global_runtime()
#     if runtime is None:
#         raise RuntimeError("Runtime is not initialized. Please call init() first.")

#     runtime._metadb.log_params(exp_id=exp_id, params=params)
