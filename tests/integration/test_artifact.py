# Test the Artifact class

import os
import tempfile

import pytest

from alphatrion.experiment.base import Experiment
from alphatrion.observe.observe import log_artifact
from alphatrion.runtime.runtime import global_runtime, init


@pytest.fixture
def artifact():
    init(project_id="test_project", artifact_insecure=True)
    artifact = global_runtime()._artifact

    yield artifact


def test_push_with_files(artifact):
    init(project_id="test_project", artifact_insecure=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is file1.")
        with open(file2, "w") as f:
            f.write("This is file2.")

        artifact.push(
            experiment_name="test_experiment", paths=[file1, file2], version="v1"
        )

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(experiment_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags


def test_push_with_folder(artifact):
    init(project_id="test_project", artifact_insecure=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is a new file1.")
        with open(file2, "w") as f:
            f.write("This is a new file2.")

        artifact.push(experiment_name="test_experiment", paths=tmpdir, version="v1")

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(experiment_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags


def test_log_artifact():
    init(project_id="test_project", artifact_insecure=True)

    with Experiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            log_artifact(paths="file1.txt", version="v1")
            versions = exp._runtime._artifact.list_versions("context_exp")
            assert "v1" in versions

            with open("file1.txt", "w") as f:
                f.write("This is modified file1.")

            # push folder instead
            log_artifact(paths=["file1.txt"], version="v2")
            versions = exp._runtime._artifact.list_versions("context_exp")
            assert "v2" in versions

        exp._runtime._artifact.delete(
            experiment_name="context_exp",
            versions=["v1", "v2"],
        )
        versions = exp._runtime._artifact.list_versions("context_exp")
        assert len(versions) == 0
