# Test the Artifact class

import os
import tempfile

import pytest

from alphatrion.artifact.artifact import Artifact
from alphatrion.experiment.base import Experiment
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def artifact():
    # We use a local registry for testing, it doesn't mean
    # it will always successfully with cloud registries.
    # We may need e2e tests for that.
    runtime = Runtime(project_id="test_project")
    artifact = Artifact(runtime=runtime, insecure=True)
    yield artifact


def test_push_with_files(artifact):
    # Create a temporary directory with some files
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is file1.")
        with open(file2, "w") as f:
            f.write("This is file2.")

        artifact.push(
            experiment_name="test_experiment", files=[file1, file2], version="v1"
        )

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(experiment_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags


def test_push_with_folder(artifact):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is a new file1.")
        with open(file2, "w") as f:
            f.write("This is a new file2.")

        artifact.push(experiment_name="test_experiment", folder=tmpdir, version="v1")

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(experiment_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags


def test_save_checkpoint():
    with Experiment.run(
        project_id="test_project",
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
        labels={"type": "unit"},
        artifact_insecure=True,
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            exp.log_artifact(1, files=["file1.txt"], version="v1")
            versions = exp._artifact.list_versions("context_exp")
            assert "v1" in versions

            with open("file1.txt", "w") as f:
                f.write("This is modified file1.")

            exp.log_artifact(1, files=["file1.txt"], version="v2")
            versions = exp._artifact.list_versions("context_exp")
            assert "v2" in versions

        exp._artifact.delete(experiment_name="context_exp", versions=["v1", "v2"])
        versions = exp._artifact.list_versions("context_exp")
        assert len(versions) == 0
