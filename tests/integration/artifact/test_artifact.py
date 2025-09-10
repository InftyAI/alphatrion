# Test the Artifact class

import os
import tempfile

import pytest

from alphatrion.artifact.artifact import Artifact
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def artifact():
    runtime = Runtime(project_id="ckpt")
    artifact = Artifact(runtime=runtime)
    yield artifact


def test_push(artifact):
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

        tags = artifact.list_tags("test_experiment")
        assert "v1" in tags

        # artifact.delete_tags(experiment_name="test_experiment", versions="v1")
        # tags = artifact.list_tags("test_experiment")
        # assert "v1" not in tags
