"""Integration tests for OCI artifact backend.

Note: These tests require a running OCI registry (like Docker Registry).

To start the test services:
    docker-compose -f docker-compose.test.yaml up -d registry

Run tests with:
    pytest tests/integration/test_oci_backend.py -v

Cleanup:
    docker-compose -f docker-compose.test.yaml down
"""

import os
import tempfile
import uuid

import pytest

import alphatrion as alpha


@pytest.fixture(autouse=True)
def oci_env_vars():
    """Set up OCI environment variables for testing."""
    original_env = {}
    env_vars = {
        "ALPHATRION_ARTIFACT_STORAGE_TYPE": "oci",
        "ALPHATRION_ARTIFACT_REGISTRY_URL": "localhost:25001",
        "ALPHATRION_ENABLE_ARTIFACT_STORAGE": "true",
    }

    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def artifact():
    """Create an artifact instance with OCI backend."""
    from alphatrion.artifact.artifact import Artifact

    return Artifact(insecure=True)


@pytest.fixture
def unique_repo():
    """Generate a unique repository name for test isolation."""
    return f"org123/team456/test-{uuid.uuid4().hex[:8]}"


def test_oci_backend_push_single_file(artifact, unique_repo):
    """Test OCI backend push with single file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Push artifact
        path = artifact.push(repo_name=unique_repo, paths=test_file, version="v1")
        assert path == f"{unique_repo}:v1"


def test_oci_backend_push_multiple_files(artifact, unique_repo):
    """Test OCI backend push with multiple files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"file{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}")
            files.append(file_path)

        # Push multiple files
        path = artifact.push(repo_name=unique_repo, paths=files, version="v2")
        assert path == f"{unique_repo}:v2"


def test_oci_backend_push_folder(artifact, unique_repo):
    """Test OCI backend push with folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files in folder
        test_dir = os.path.join(tmpdir, "test_folder")
        os.makedirs(test_dir)

        for i in range(3):
            with open(os.path.join(test_dir, f"file{i}.txt"), "w") as f:
                f.write(f"content {i}")

        # Push folder
        path = artifact.push(repo_name=unique_repo, paths=test_dir, version="v3")
        assert path == f"{unique_repo}:v3"


def test_oci_backend_push_auto_version(artifact, unique_repo):
    """Test OCI backend push with auto-generated version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Push without version
        path = artifact.push(repo_name=unique_repo, paths=test_file)

        # Should return repo_name:auto_version
        assert path.startswith(f"{unique_repo}:")


def test_oci_backend_push_empty_files_error(artifact, unique_repo):
    """Test OCI backend push with no files raises error."""
    with pytest.raises(ValueError, match="no files specified to push"):
        artifact.push(repo_name=unique_repo, paths=None, version="v1")

    with pytest.raises(ValueError, match="no files specified to push"):
        artifact.push(repo_name=unique_repo, paths="", version="v1")


def test_oci_backend_push_empty_folder_error(artifact, unique_repo):
    """Test OCI backend push with empty folder raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty folder
        empty_dir = os.path.join(tmpdir, "empty")
        os.makedirs(empty_dir)

        with pytest.raises(ValueError, match="No files to push"):
            artifact.push(repo_name=unique_repo, paths=empty_dir, version="v1")


def test_oci_backend_list_versions(artifact, unique_repo):
    """Test OCI backend list_versions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple versions
        for i in range(3):
            test_file = os.path.join(tmpdir, f"test{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"content {i}")

            artifact.push(repo_name=unique_repo, paths=test_file, version=f"v{i}")

        # List versions
        versions = artifact.list_versions(unique_repo)
        assert len(versions) == 3
        assert "v0" in versions
        assert "v1" in versions
        assert "v2" in versions


def test_oci_backend_list_versions_empty(artifact):
    """Test list_versions returns empty list for non-existent repo."""
    versions = artifact.list_versions("org123/team456/nonexistent")
    assert versions == []


def test_oci_backend_pull_single_file(artifact, unique_repo):
    """Test OCI backend pull."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Push a file
        test_file = os.path.join(tmpdir, "checkpoint.pt")
        with open(test_file, "w") as f:
            f.write("model weights")

        artifact.push(repo_name=unique_repo, paths=test_file, version="v1")

        # Pull the file
        output_dir = os.path.join(tmpdir, "download")
        result = artifact.pull(
            repo_name=unique_repo, version="v1", output_dir=output_dir
        )

        # Verify file was downloaded
        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]) == "checkpoint.pt"

        # Verify content
        with open(result[0]) as f:
            assert f.read() == "model weights"


def test_oci_backend_pull_multiple_files(artifact, unique_repo):
    """Test pull with multiple files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple files
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"file{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}")
            files.append(file_path)

        artifact.push(repo_name=unique_repo, paths=files, version="v1")

        # Pull the files
        output_dir = os.path.join(tmpdir, "download")
        result = artifact.pull(
            repo_name=unique_repo, version="v1", output_dir=output_dir
        )

        # Verify all files were downloaded
        assert len(result) == 3

        # Check that all expected files exist and have correct content
        result_basenames = [os.path.basename(r) for r in result]
        for i in range(3):
            expected_filename = f"file{i}.txt"
            assert expected_filename in result_basenames

            expected_file = os.path.join(output_dir, expected_filename)
            assert os.path.exists(expected_file)

            with open(expected_file) as f:
                assert f.read() == f"content {i}"


def test_oci_backend_pull_to_current_dir(artifact, unique_repo):
    """Test pull without output_dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Push a file
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            artifact.push(repo_name=unique_repo, paths=test_file, version="v1")

            # Pull without output_dir
            result = artifact.pull(repo_name=unique_repo, version="v1")

            # Should download to current directory
            assert len(result) == 1
            assert os.path.basename(result[0]) == "test.txt"
            assert os.path.exists(result[0])

            with open(result[0]) as f:
                assert f.read() == "test content"
        finally:
            os.chdir(original_dir)


def test_oci_backend_delete(artifact, unique_repo):
    """Test OCI backend delete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple versions with different content
        test_file1 = os.path.join(tmpdir, "test1.txt")
        with open(test_file1, "w") as f:
            f.write("test content v1")
        artifact.push(repo_name=unique_repo, paths=test_file1, version="v1")

        test_file2 = os.path.join(tmpdir, "test2.txt")
        with open(test_file2, "w") as f:
            f.write("test content v2")
        artifact.push(repo_name=unique_repo, paths=test_file2, version="v2")

        # Verify both versions exist
        versions = artifact.list_versions(unique_repo)
        assert "v1" in versions
        assert "v2" in versions

        # Delete v1
        artifact.delete(repo_name=unique_repo, versions="v1")

        # Verify v1 is deleted
        versions = artifact.list_versions(unique_repo)
        assert "v1" not in versions
        assert "v2" in versions


def test_oci_backend_delete_multiple_versions(artifact, unique_repo):
    """Test deleting multiple versions at once."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple versions with DIFFERENT content (so they have different blobs)
        for i in range(3):
            test_file = os.path.join(tmpdir, f"test{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"test content version {i}")  # Different content per version

            artifact.push(repo_name=unique_repo, paths=test_file, version=f"v{i}")

        # Verify all versions exist before delete
        versions_before = artifact.list_versions(unique_repo)
        assert len(versions_before) == 3

        # Delete v0 and v1
        artifact.delete(repo_name=unique_repo, versions=["v0", "v1"])

        # Verify only v2 remains
        versions = artifact.list_versions(unique_repo)
        assert "v0" not in versions
        assert "v1" not in versions
        assert "v2" in versions


@pytest.mark.asyncio
async def test_load_checkpoint_latest(artifact):
    """Test load_checkpoint with 'latest' tag."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple checkpoint versions with different content and timestamps
        import time

        for i in range(3):
            test_file = os.path.join(tmpdir, f"checkpoint_{i}.pt")
            with open(test_file, "w") as f:
                f.write(f"model weights version {i}")

            artifact.push(
                repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
                paths=test_file,
                version=f"v{i}",
            )
            if i < 2:
                time.sleep(0.1)  # Small delay for timestamp ordering

        # Load latest checkpoint (should be v2 for S3, but arbitrary for OCI)
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version="latest", output_dir=output_dir
        )

        # Verify checkpoint was downloaded
        assert result is not None
        assert len(result) == 1
        assert os.path.exists(result[0])

        # Verify it's one of the versions
        with open(result[0]) as f:
            content = f.read()
            assert content.startswith("model weights version")


@pytest.mark.asyncio
async def test_load_checkpoint_specific_version(artifact):
    """Test load_checkpoint with specific version tag."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple checkpoint versions
        for i in range(3):
            test_file = os.path.join(tmpdir, f"checkpoint_{i}.pt")
            with open(test_file, "w") as f:
                f.write(f"model weights version {i}")

            artifact.push(
                repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
                paths=test_file,
                version=f"v{i}",
            )

        # Load specific version v1
        output_dir = os.path.join(tmpdir, "download")

        # Verify output_dir doesn't exist yet
        assert not os.path.exists(output_dir), (
            "Output dir should not exist before load_checkpoint"
        )

        result = await alpha.load_checkpoint(
            id=exp_id, version="v1", output_dir=output_dir
        )

        # Validate output_dir was created
        assert os.path.exists(output_dir), (
            "Output dir should be created by load_checkpoint"
        )
        assert os.path.isdir(output_dir), "Output path should be a directory"

        # Validate results
        assert result is not None
        assert len(result) == 1

        # Validate file is in the correct output directory
        downloaded_file = result[0]
        # Use realpath to resolve symlinks (e.g., /var -> /private/var on macOS)
        real_downloaded = os.path.realpath(downloaded_file)
        real_output_dir = os.path.realpath(output_dir)
        assert real_downloaded.startswith(real_output_dir), (
            f"File {real_downloaded} should be in output_dir {real_output_dir}"
        )

        # Verify the file actually exists in output_dir
        filename = os.path.basename(downloaded_file)
        expected_path = os.path.join(output_dir, filename)
        assert os.path.exists(expected_path), f"File should exist at {expected_path}"

        # Verify it's the correct version
        with open(result[0]) as f:
            content = f.read()
            assert content == "model weights version 1"


@pytest.mark.asyncio
async def test_load_checkpoint_nonexistent(artifact):
    """Test load_checkpoint returns None for nonexistent experiment."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Try to load checkpoint from non-existent experiment
        result = await alpha.load_checkpoint(
            id=exp_id, version="latest", output_dir=tmpdir
        )

        assert result == []


@pytest.mark.asyncio
async def test_load_checkpoint_multiple_files(artifact):
    """Test load_checkpoint with multiple files in checkpoint."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push checkpoint with multiple files
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"layer_{i}.pt")
            with open(file_path, "w") as f:
                f.write(f"layer {i} weights")
            files.append(file_path)

        artifact.push(
            repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt", paths=files, version="v1"
        )

        # Load checkpoint
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version="v1", output_dir=output_dir
        )

        # Verify all files were downloaded
        assert result is not None
        assert len(result) == 3

        for i in range(3):
            filename = f"layer_{i}.pt"
            assert any(filename in r for r in result)

            file_path = os.path.join(output_dir, filename)
            assert os.path.exists(file_path)

            with open(file_path) as f:
                assert f.read() == f"layer {i} weights"
