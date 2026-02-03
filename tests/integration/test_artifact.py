# Test the Artifact class

import os
import tempfile
import uuid

import pytest

import alphatrion as alpha
from alphatrion.runtime.runtime import global_runtime


@pytest.fixture
def artifact():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    artifact = global_runtime()._artifact

    yield artifact


def test_push_with_files(artifact):
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is file1.")
        with open(file2, "w") as f:
            f.write("This is file2.")

        artifact.push(repo_name="test_experiment", paths=[file1, file2], version="v1")

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(repo_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags


def test_push_with_folder(artifact):
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        file1 = "file1.txt"
        file2 = "file2.txt"
        with open(file1, "w") as f:
            f.write("This is a new file1.")
        with open(file2, "w") as f:
            f.write("This is a new file2.")

        artifact.push(repo_name="test_experiment", paths=tmpdir, version="v1")

        tags = artifact.list_versions("test_experiment")
        assert "v1" in tags

        artifact.delete(repo_name="test_experiment", versions="v1")
        tags = artifact.list_versions("test_experiment")
        assert "v1" not in tags
