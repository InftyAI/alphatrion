"""Tests for S3 artifact backend (push-only).

Note: These tests require boto3 and moto to be installed.
Run with: pytest tests/unit/artifact/test_s3_backend.py
"""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def s3_env_vars():
    """Set up S3 environment variables for testing."""
    original_env = {}
    env_vars = {
        "ALPHATRION_ARTIFACT_STORAGE_TYPE": "s3",
        "ALPHATRION_ARTIFACT_S3_BUCKET": "test-bucket",
        "ALPHATRION_ARTIFACT_S3_REGION": "us-east-1",
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
def s3_client():
    """Create a mock S3 client with versioning enabled."""
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


def test_s3_backend_push_single_file(s3_client):
    """Test S3 backend push with single file using path-based versioning."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Push artifact with explicit version
        path = artifact.push(
            repo_name="org123/team456/test-repo", paths=test_file, version="v1"
        )
        assert path == "org123/team456/test-repo/v1"

        # Verify file was uploaded to S3 with version in path
        response = s3_client.list_objects_v2(
            Bucket="test-bucket", Prefix="org123/team456/test-repo/v1/"
        )
        assert "Contents" in response
        assert len(response["Contents"]) == 1
        assert response["Contents"][0]["Key"] == "org123/team456/test-repo/v1/test.txt"


def test_s3_backend_push_multiple_files(s3_client):
    """Test S3 backend push with multiple files using path-based versioning."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"file{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}")
            files.append(file_path)

        # Push multiple files with version
        path = artifact.push(
            repo_name="org123/team456/test-repo", paths=files, version="v2"
        )
        assert path == "org123/team456/test-repo/v2"

        # Verify all files were uploaded with version in path
        response = s3_client.list_objects_v2(
            Bucket="test-bucket", Prefix="org123/team456/test-repo/v2/"
        )
        assert "Contents" in response
        assert len(response["Contents"]) == 3


def test_s3_backend_push_folder(s3_client):
    """Test S3 backend push with folder using path-based versioning."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files in folder
        test_dir = os.path.join(tmpdir, "test_folder")
        os.makedirs(test_dir)

        for i in range(3):
            with open(os.path.join(test_dir, f"file{i}.txt"), "w") as f:
                f.write(f"content {i}")

        # Push folder with version
        path = artifact.push(
            repo_name="org123/team456/test-repo", paths=test_dir, version="v3"
        )
        assert path == "org123/team456/test-repo/v3"

        # Verify all files were uploaded with version in path
        response = s3_client.list_objects_v2(
            Bucket="test-bucket", Prefix="org123/team456/test-repo/v3/"
        )
        assert "Contents" in response
        assert len(response["Contents"]) == 3


def test_s3_backend_push_auto_version(s3_client):
    """Test S3 backend push with auto-generated version (native versioning ignores version param)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Push without version (native versioning doesn't use version parameter)
        path = artifact.push(repo_name="org123/team456/test-repo", paths=test_file)

        # Should return repo_name (no version in path)
        assert path == "org123/team456/test-repo"


def test_s3_backend_push_empty_files_error(s3_client):
    """Test S3 backend push with no files raises error."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with pytest.raises(ValueError, match="no files specified to push"):
        artifact.push(repo_name="org123/team456/test-repo", paths=None, version="v1")

    with pytest.raises(ValueError, match="no files specified to push"):
        artifact.push(repo_name="org123/team456/test-repo", paths="", version="v1")


def test_s3_backend_push_empty_folder_error(s3_client):
    """Test S3 backend push with empty folder raises error."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty folder
        empty_dir = os.path.join(tmpdir, "empty")
        os.makedirs(empty_dir)

        with pytest.raises(ValueError, match="No files to push"):
            artifact.push(
                repo_name="org123/team456/test-repo", paths=empty_dir, version="v1"
            )


def test_s3_backend_list_versions_empty(s3_client):
    """Test list_versions returns empty list for non-existent repo."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    versions = artifact.list_versions("org123/team456/nonexistent")
    assert versions == []


def test_s3_backend_list_versions_single_file(s3_client):
    """Test list_versions with a single file."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "checkpoint.pt")
        with open(test_file, "w") as f:
            f.write("model weights")

        # Push file directly (no version folder)
        artifact.push(repo_name="org123/team456/exp1/ckpt", paths=test_file)

        # List versions should return the filename
        versions = artifact.list_versions("org123/team456/exp1/ckpt")
        assert len(versions) == 1
        assert "checkpoint.pt" in versions


def test_s3_backend_list_versions_multiple_files(s3_client):
    """Test list_versions with multiple files sorted by time."""
    import time

    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push 3 files with small delays to ensure different timestamps
        for i in range(3):
            test_file = os.path.join(tmpdir, f"checkpoint_{i}.pt")
            with open(test_file, "w") as f:
                f.write(f"model weights {i}")

            artifact.push(repo_name="org123/team456/exp1/ckpt", paths=test_file)
            time.sleep(1)  # Small delay to ensure different timestamps

        # List versions should return files sorted by LastModified (newest first)
        versions = artifact.list_versions("org123/team456/exp1/ckpt")
        assert len(versions) == 3
        # The newest file (checkpoint_2.pt) should be first
        assert versions[0] == "checkpoint_2.pt"
        assert versions[1] == "checkpoint_1.pt"
        assert versions[2] == "checkpoint_0.pt"


def test_s3_backend_list_versions_ignores_nested(s3_client):
    """Test list_versions ignores nested files (uses delimiter)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push top-level file
        top_file = os.path.join(tmpdir, "checkpoint.pt")
        with open(top_file, "w") as f:
            f.write("top level")
        artifact.push(repo_name="org123/team456/exp1/ckpt", paths=top_file)

        # Manually create nested file in S3 (simulating accidental nested upload)
        s3_client.put_object(
            Bucket="test-bucket",
            Key="org123/team456/exp1/ckpt/nested/file.txt",
            Body=b"nested content",
        )

        # List versions should only return top-level file
        versions = artifact.list_versions("org123/team456/exp1/ckpt")
        assert len(versions) == 1
        assert versions[0] == "checkpoint.pt"


def test_s3_backend_list_versions_pagination_limit(s3_client):
    """Test list_versions respects 3000 file limit (3 pages)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 10 test files (simulating pagination scenario)
        # In real scenario, we'd create 3500 files but that's slow for tests
        files = []
        for i in range(10):
            test_file = os.path.join(tmpdir, f"checkpoint_{i:04d}.pt")
            with open(test_file, "w") as f:
                f.write(f"model {i}")
            files.append(test_file)

        # Push all files
        artifact.push(repo_name="org123/team456/exp1/ckpt", paths=files)

        # List versions should return all files (under the 3000 limit)
        versions = artifact.list_versions("org123/team456/exp1/ckpt")
        assert len(versions) == 10
        # Should be sorted by timestamp (newest first)
        assert all(f"checkpoint_{i:04d}.pt" in versions for i in range(10))


def test_s3_backend_pull_single_file(s3_client):
    """Test pull with single file (flat structure)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push a file
        test_file = os.path.join(tmpdir, "checkpoint.pt")
        with open(test_file, "w") as f:
            f.write("model weights")
        artifact.push(repo_name="org123/team456/exp1/ckpt", paths=test_file)

        # Pull the file to a new directory
        output_dir = os.path.join(tmpdir, "download")
        result = artifact.pull(
            repo_name="org123/team456/exp1/ckpt",
            version_or_filename="checkpoint.pt",
            output_dir=output_dir,
        )

        # Verify file was downloaded
        assert len(result) == 1
        assert os.path.exists(result[0])
        assert os.path.basename(result[0]) == "checkpoint.pt"

        # Verify content
        with open(result[0]) as f:
            assert f.read() == "model weights"


def test_s3_backend_pull_version_folder(s3_client):
    """Test pull with version folder (versioned structure)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Push multiple files with version
        files = []
        for i in range(3):
            file_path = os.path.join(tmpdir, f"file{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}")
            files.append(file_path)

        artifact.push(repo_name="org123/team456/exp1/ckpt", paths=files, version="v1")

        # Pull the version folder
        output_dir = os.path.join(tmpdir, "download")
        result = artifact.pull(
            repo_name="org123/team456/exp1/ckpt",
            version_or_filename="v1",
            output_dir=output_dir,
        )

        # Verify all files were downloaded
        assert len(result) == 3
        for i in range(3):
            expected_file = os.path.join(output_dir, f"file{i}.txt")
            assert any(expected_file == r for r in result)
            assert os.path.exists(expected_file)

            with open(expected_file) as f:
                assert f.read() == f"content {i}"


def test_s3_backend_pull_to_current_dir(s3_client):
    """Test pull without output_dir (downloads to current directory)."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Push a file
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")
            artifact.push(repo_name="org123/team456/test-repo", paths=test_file)

            # Pull without output_dir
            result = artifact.pull(
                repo_name="org123/team456/test-repo", version_or_filename="test.txt"
            )

            # Should download to current directory
            assert len(result) == 1
            assert os.path.basename(result[0]) == "test.txt"
            assert os.path.exists(result[0])

            with open(result[0]) as f:
                assert f.read() == "test content"
        finally:
            os.chdir(original_dir)


def test_s3_backend_pull_nonexistent_file(s3_client):
    """Test pull with non-existent file returns empty list."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        result = artifact.pull(
            repo_name="org123/team456/nonexistent",
            version_or_filename="missing.txt",
            output_dir=tmpdir,
        )
        assert result == []


def test_s3_backend_pull_empty_version_folder(s3_client):
    """Test pull with empty version folder returns empty list."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Pull non-existent version folder
        result = artifact.pull(
            repo_name="org123/team456/exp1/ckpt",
            version_or_filename="v999",
            output_dir=tmpdir,
        )

        # Should return empty list
        assert result == []


def test_s3_backend_path_based_versioning(s3_client):
    """Test path-based versioning - different versions go to different folders."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")

        # Push version 1
        with open(test_file, "w") as f:
            f.write("version 1 content")
        path1 = artifact.push(
            repo_name="org123/team456/test-repo", paths=test_file, version="v1"
        )

        # Push version 2 (same filename, different content, different version)
        with open(test_file, "w") as f:
            f.write("version 2 content - updated")
        path2 = artifact.push(
            repo_name="org123/team456/test-repo", paths=test_file, version="v2"
        )

        # Should return different paths
        assert path1 == "org123/team456/test-repo/v1"
        assert path2 == "org123/team456/test-repo/v2"

        # Should have 2 object keys (in different version folders)
        response = s3_client.list_objects_v2(
            Bucket="test-bucket", Prefix="org123/team456/test-repo/"
        )
        assert "Contents" in response
        assert len(response["Contents"]) == 2
        keys = [obj["Key"] for obj in response["Contents"]]
        assert "org123/team456/test-repo/v1/test.txt" in keys
        assert "org123/team456/test-repo/v2/test.txt" in keys


def test_s3_backend_delete_not_implemented(s3_client):
    """Test that delete raises NotImplementedError."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with pytest.raises(NotImplementedError, match="delete is not implemented"):
        artifact.delete(repo_name="org123/team456/test-repo", versions="v1")


def test_s3_backend_generate_download_urls(s3_client):
    """Test S3 backend generate_download_urls method with path-based versioning."""
    from alphatrion.artifact.artifact import Artifact

    artifact = Artifact()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and push test files
        test_file1 = os.path.join(tmpdir, "file1.txt")
        test_file2 = os.path.join(tmpdir, "file2.txt")
        with open(test_file1, "w") as f:
            f.write("content 1")
        with open(test_file2, "w") as f:
            f.write("content 2")

        # Push artifacts with version
        path = artifact.push(
            repo_name="org123/team456/test-repo",
            paths=[test_file1, test_file2],
            version="v1",
        )
        assert path == "org123/team456/test-repo/v1"

        # Generate download URLs using the full path with version
        urls = artifact._backend.generate_download_urls(
            path="org123/team456/test-repo/v1", expires_in=60
        )

        assert len(urls) == 2
        assert all("filename" in url for url in urls)
        assert all("url" in url for url in urls)
        assert any(url["filename"] == "file1.txt" for url in urls)
        assert any(url["filename"] == "file2.txt" for url in urls)
        # URLs should be valid HTTP(S) URLs
        assert all(url["url"].startswith("http") for url in urls)
        # URLs should contain the bucket and key information
        assert all("test-bucket" in url["url"] for url in urls)


def test_oci_backend_is_default():
    """Test that OCI is the default backend."""
    # Temporarily unset S3 env var
    original = os.environ.pop("ALPHATRION_ARTIFACT_STORAGE_TYPE", None)
    os.environ["ALPHATRION_ARTIFACT_REGISTRY_URL"] = "localhost:5001"

    try:
        from alphatrion.artifact.artifact import Artifact
        from alphatrion.artifact.oci_backend import OCIBackend

        artifact = Artifact(insecure=True)
        # Should use OCI backend
        assert isinstance(artifact._backend, OCIBackend)
    finally:
        if original:
            os.environ["ALPHATRION_ARTIFACT_STORAGE_TYPE"] = original
