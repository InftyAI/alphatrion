# Test the Artifact class


import pytest

from alphatrion.runtime.runtime import global_runtime, init


@pytest.fixture
def artifact():
    init(project_id="test_project", artifact_insecure=True)
    artifact = global_runtime()._artifact
    yield artifact


def test_push_with_error_folder(artifact):
    with pytest.raises(RuntimeError):
        artifact.push(
            repo_name="test_experiment",
            paths="non_existent_folder.txt",
            version="v1",
        )


def test_push_with_empty_folder(artifact):
    with pytest.raises(RuntimeError):
        artifact.push(
            repo_name="test_experiment",
            paths="empty_folder",
            version="v1",
        )
