"""Integration tests for S3 artifact backend with load_checkpoint.

Note: These tests use moto to mock AWS S3 for integration testing.

Run tests with:
    pytest tests/integration/test_s3_backend.py -v
"""

import os
import tempfile
import uuid

import pytest

import alphatrion as alpha
import alphatrion.storage.runtime as storage_runtime_module


@pytest.fixture(autouse=True)
def s3_env_vars():
    """Set up S3 environment variables for testing."""
    original_env = {}

    # Reset storage runtime to ensure it picks up new env vars
    storage_runtime_module.__STORAGE_RUNTIME__ = None

    # Environment variables to set for S3
    env_vars = {
        "ALPHATRION_ARTIFACT_STORAGE_TYPE": "s3",
        "ALPHATRION_ARTIFACT_S3_BUCKET": "test-bucket",
        "ALPHATRION_ARTIFACT_S3_REGION": "us-east-1",
        "ALPHATRION_ENABLE_ARTIFACT_STORAGE": "true",
    }

    # Save original values and set S3 variables
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

    storage_runtime_module.__STORAGE_RUNTIME__ = (
        None  # Reset again to clear any cached runtime
    )


@pytest.fixture
def mock_s3():
    """Create a mock AWS context for S3 testing."""
    try:
        from moto import mock_aws
    except ImportError:
        pytest.skip("moto is required for S3 backend tests")

    with mock_aws():
        import boto3

        # Create the bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        # Enable versioning on the bucket for native versioning support
        s3.put_bucket_versioning(
            Bucket="test-bucket", VersioningConfiguration={"Status": "Enabled"}
        )

        yield s3


@pytest.fixture
def artifact(mock_s3):
    """Create an artifact instance with S3 backend.

    This fixture depends on mock_s3 to ensure the mock context is active.
    """
    from alphatrion.artifact.artifact import Artifact

    return Artifact()


@pytest.mark.asyncio
async def test_load_checkpoint_by_filename(artifact, mock_s3):
    """Test load_checkpoint by filename for S3 backend."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple checkpoints as separate files (S3 flat structure)
        for i in range(3):
            test_file = os.path.join(tmpdir, f"checkpoint_{i}.pt")
            with open(test_file, "w") as f:
                f.write(f"model weights version {i}")

            artifact.push(
                repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
                paths=test_file,
            )

        # Load specific checkpoint by filename
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version_or_filename="checkpoint_1.pt", output_dir=output_dir
        )

        # Verify checkpoint was downloaded
        assert result is not None
        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]) == "checkpoint_1.pt"

        # Verify content
        with open(result[0]) as f:
            content = f.read()
            assert content == "model weights version 1"


@pytest.mark.asyncio
async def test_load_checkpoint_filename_with_dot(artifact, mock_s3):
    """Test load_checkpoint with filename containing dots (e.g., checkpoint.v1.0.pt)."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push checkpoint with filename containing dots
        test_file = os.path.join(tmpdir, "checkpoint.v1.0.pt")
        with open(test_file, "w") as f:
            f.write("model weights version 1.0")

        artifact.push(
            repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
            paths=test_file,
        )

        # Load checkpoint by filename with dots
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version_or_filename="checkpoint.v1.0.pt", output_dir=output_dir
        )

        # Verify checkpoint was downloaded
        assert result is not None
        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]) == "checkpoint.v1.0.pt"

        # Verify content
        with open(result[0]) as f:
            content = f.read()
            assert content == "model weights version 1.0"


@pytest.mark.asyncio
async def test_load_checkpoint_nonexistent(artifact, mock_s3):
    """Test load_checkpoint with nonexistent checkpoint returns empty list for S3."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # For S3, trying to pull a non-existent version/folder should return empty list
        result = await alpha.load_checkpoint(
            id=exp_id, version_or_filename="nonexistent", output_dir=tmpdir
        )
        assert result == []


@pytest.mark.asyncio
async def test_load_checkpoint_folder(artifact, mock_s3):
    """Test load_checkpoint loading all files from a folder prefix for S3 backend."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push checkpoint with multiple files in a folder
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"layer_{i}.pt")
            with open(file_path, "w") as f:
                f.write(f"layer {i} weights")
            files.append(file_path)

        # Push to a folder path (e.g., "epoch_10")
        artifact.push(
            repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
            paths=files,
            version="epoch_10",
        )

        # Load all files from the folder
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version_or_filename="epoch_10", output_dir=output_dir
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


@pytest.mark.asyncio
async def test_load_checkpoint_single_file(artifact, mock_s3):
    """Test load_checkpoint pulling a single file directly (flat structure)."""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = uuid.uuid4()

    alpha.init(org_id=org_id, team_id=team_id, user_id=user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push checkpoint without version (flat structure)
        test_file = os.path.join(tmpdir, "checkpoint.pt")
        with open(test_file, "w") as f:
            f.write("model weights")

        artifact.push(
            repo_name=f"{org_id}/{team_id}/{exp_id}/ckpt",
            paths=test_file,
        )

        # Load checkpoint by filename
        output_dir = os.path.join(tmpdir, "download")
        result = await alpha.load_checkpoint(
            id=exp_id, version_or_filename="checkpoint.pt", output_dir=output_dir
        )

        # Verify file was downloaded
        assert result is not None
        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]) == "checkpoint.pt"

        # Verify content
        with open(result[0]) as f:
            assert f.read() == "model weights"
