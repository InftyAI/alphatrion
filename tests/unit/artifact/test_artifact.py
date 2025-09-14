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


def test_push_with_error_folder(artifact):
    with pytest.raises(RuntimeError):
        artifact.push(
            experiment_name="test_experiment",
            paths="non_existent_folder.txt",
            version="v1",
        )


def test_push_with_empty_folder(artifact):
    with pytest.raises(RuntimeError):
        artifact.push(
            experiment_name="test_experiment",
            paths="empty_folder",
            version="v1",
        )
