# Test the Artifact class


import pytest

from alphatrion.artifact.artifact import Artifact
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def artifact():
    # We use a local registry for testing, it doesn't mean
    # it will always successfully with cloud registries.
    # We may need e2e tests for that.
    runtime = Runtime(project_id="test_project")
    artifact = Artifact(runtime=runtime, insecure=True)
    yield artifact


def test_push_with_both_files_and_folder(artifact):
    with pytest.raises(ValueError):
        artifact.push(
            experiment_name="test_experiment",
            files=["file1.txt"],
            folder="some_folder",
            version="v1",
        )


def test_push_with_error_folder(artifact):
    with pytest.raises(ValueError):
        artifact.push(
            experiment_name="test_experiment",
            folder="non_existent_folder.txt",
            version="v1",
        )


def test_push_with_no_files_and_no_folder(artifact):
    with pytest.raises(ValueError):
        artifact.push(
            experiment_name="test_experiment",
            version="v1",
        )
