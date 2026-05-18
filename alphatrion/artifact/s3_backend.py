"""S3-compatible artifact storage backend (push-only).

This backend supports pushing artifacts to S3 for archival/backup purposes.
list_versions() and pull() are not implemented - use AWS S3 console, CLI,
or SDK directly to retrieve artifacts if needed.
"""

import os

from alphatrion import envs
from alphatrion.artifact.base import ArtifactStorageBackend


class S3Backend(ArtifactStorageBackend):
    """S3-compatible storage backend (push-only).

    Supports pushing artifacts to S3. To retrieve artifacts,
    use AWS S3 console, CLI, or SDK directly.
    """

    def __init__(self):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError(
                "boto3 is required for S3 backend. Install it with: pip install alphatrion[s3]"
            ) from e

        self._bucket = os.environ.get(envs.ARTIFACT_S3_BUCKET)
        if not self._bucket:
            raise RuntimeError("ARTIFACT_S3_BUCKET not configured")

        endpoint_url = os.environ.get(envs.ARTIFACT_S3_ENDPOINT)
        region = os.environ.get(envs.ARTIFACT_S3_REGION)
        access_key = os.environ.get(envs.ARTIFACT_S3_ACCESS_KEY)
        secret_key = os.environ.get(envs.ARTIFACT_S3_SECRET_KEY)

        session_kwargs = {}
        if access_key and secret_key:
            session_kwargs["aws_access_key_id"] = access_key
            session_kwargs["aws_secret_access_key"] = secret_key

        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            **session_kwargs,
        )

    def push(
        self,
        repo_name: str,
        paths: str | list[str],
        version: str | None = None,
    ) -> str:
        """Push artifacts to S3 with optional path-based versioning.

        If version is provided, files are organized in version folders (path-based).
        If version is None, files are uploaded directly (S3 native versioning as backup).

        :param repo_name: Repository name (e.g., "org_id/team_id/exp_id/repo")
        :param paths: File path(s) to upload
        :param version: Optional version string. If provided, creates version folders.
        :return: S3 path - "repo_name/version" if version provided, else "repo_name"
        """
        if paths is None or not paths:
            raise ValueError("no files specified to push")

        if isinstance(paths, str):
            if os.path.isdir(paths):
                files_to_push = [
                    os.path.join(paths, f)
                    for f in os.listdir(paths)
                    if os.path.isfile(os.path.join(paths, f))
                ]
            else:
                files_to_push = [paths]
        else:
            files_to_push = paths

        if not files_to_push:
            raise ValueError("No files to push.")

        try:
            for file_path in files_to_push:
                filename = os.path.basename(file_path)
                # No version in path - S3 native versioning handles it
                s3_key = f"{repo_name}/{filename}"
                if version is not None:
                    # Optionally, we could include the version in the key for organizational purposes,
                    # but S3 will still generate its own version ID for each upload.
                    s3_key = f"{repo_name}/{version}/{filename}"

                # upload_file works with native versioning and handles large files better
                self._s3.upload_file(file_path, self._bucket, s3_key)
                # Note: S3 automatically creates new versions for each upload
                # Use list_object_versions() to retrieve version IDs later if needed

        except Exception as e:
            raise RuntimeError(f"Failed to push artifacts to S3: {e}") from e

        # Return repo_name (path format without version)
        # Note: Each file has its own VersionId managed by S3
        return repo_name if version is None else f"{repo_name}/{version}"

    def list_versions(self, repo_name: str) -> list[str]:
        """List all files directly under a repository path (ignores nested files).

        Returns at most 3000 files (3 pages). If you have more checkpoints than this,
        consider using database metadata to track versions instead.

        :param repo_name: Repository path (e.g., "org_id/team_id/exp_id/ckpt")
        :return: List of filenames sorted by LastModified (newest first), max 3000 items
        """
        try:
            prefix = f"{repo_name}/"
            files_with_time = []
            continuation_token = None
            max_pages = 3  # Limit to 3000 files (1000 per page)
            pages_fetched = 0

            # Handle pagination for >1000 files, up to max_pages
            while pages_fetched < max_pages:
                # Use delimiter to only list top-level files, ignoring nested directories
                params = {
                    "Bucket": self._bucket,
                    "Prefix": prefix,
                    "Delimiter": "/",
                }
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = self._s3.list_objects_v2(**params)
                pages_fetched += 1

                if "Contents" in response:
                    # Extract filenames and timestamps
                    for obj in response["Contents"]:
                        s3_key = obj["Key"]
                        # Get filename: "repo_name/file.txt" -> "file.txt"
                        filename = s3_key[len(prefix) :]
                        if filename:  # Skip empty
                            files_with_time.append((filename, obj["LastModified"]))

                # Check if there are more results
                if response.get("IsTruncated") and pages_fetched < max_pages:
                    continuation_token = response.get("NextContinuationToken")
                else:
                    break

            if not files_with_time:
                return []

            # Sort by LastModified descending (newest first)
            files_with_time.sort(key=lambda x: x[1], reverse=True)

            return [f[0] for f in files_with_time]
        except Exception as e:
            error_msg = str(e).lower()
            if (
                "404" in error_msg
                or "not found" in error_msg
                or "nosuchbucket" in error_msg
            ):
                return []
            raise RuntimeError(f"Failed to list versions: {e}") from e

    def pull(
        self, repo_name: str, version: str, output_dir: str | None = None
    ) -> list[str]:
        """Pull (download) files from S3.

        :param repo_name: Repository path (e.g., "org_id/team_id/exp_id/ckpt")
        :param version: The filename to download (for flat structure) or folder name (for versioned structure)
        :param output_dir: Optional directory to save files. If None, downloads to current directory.
        :return: List of absolute paths to downloaded files
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            download_dir = os.path.abspath(output_dir)
        else:
            download_dir = os.getcwd()

        try:
            # Check if version looks like a filename (has extension) or version folder
            if "." in version:
                # Single file: repo_name/version (e.g., "ckpt/checkpoint_123.pt")
                s3_key = f"{repo_name}/{version}"
                local_path = os.path.join(download_dir, version)

                self._s3.download_file(self._bucket, s3_key, local_path)
                return [local_path]
            else:
                # Version folder: repo_name/version/* (e.g., "ckpt/v1/*")
                prefix = f"{repo_name}/{version}/"

                response = self._s3.list_objects_v2(
                    Bucket=self._bucket, Prefix=prefix, Delimiter="/"
                )

                if "Contents" not in response:
                    return []

                downloaded_files = []
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    filename = s3_key[len(prefix) :]
                    if filename:  # Skip empty/directory markers
                        local_path = os.path.join(download_dir, filename)
                        self._s3.download_file(self._bucket, s3_key, local_path)
                        downloaded_files.append(local_path)

                return downloaded_files
        except Exception as e:
            raise RuntimeError(f"Failed to pull artifacts from S3: {e}") from e

    def delete(self, repo_name: str, versions: str | list[str]):
        raise NotImplementedError("delete is not implemented for S3 backend")

    def generate_download_urls(
        self, path: str, version: str | None = None, expires_in: int = 30
    ) -> list[dict[str, str]]:
        """Generate presigned URLs for downloading artifacts from S3 with native versioning.

        :param path: Repository path (e.g., "org_id/team_id/exp_id/repo")
        :param version: Optional specific version ID to download. If None, downloads latest versions.
        :param expires_in: URL expiration time in seconds (default: 30 seconds)
        :return: List of dicts with 'filename' and 'url' keys
        """
        try:
            prefix = f"{path}/"

            if version:
                # Get specific version
                response = self._s3.list_object_versions(
                    Bucket=self._bucket, Prefix=prefix
                )

                if "Versions" not in response:
                    return []

                download_urls = []
                for obj in response["Versions"]:
                    if obj["VersionId"] == version:
                        s3_key = obj["Key"]
                        filename = os.path.basename(s3_key)

                        url = self._s3.generate_presigned_url(
                            "get_object",
                            Params={
                                "Bucket": self._bucket,
                                "Key": s3_key,
                                "VersionId": version,
                            },
                            ExpiresIn=expires_in,
                        )

                        download_urls.append({"filename": filename, "url": url})

                return download_urls
            else:
                # Get latest versions of all files
                response = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)

                if "Contents" not in response:
                    return []

                download_urls = []
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    filename = os.path.basename(s3_key)

                    # Generate presigned URL for latest version
                    url = self._s3.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": self._bucket, "Key": s3_key},
                        ExpiresIn=expires_in,
                    )

                    download_urls.append({"filename": filename, "url": url})

                return download_urls
        except Exception as e:
            raise RuntimeError(f"Failed to generate download URLs: {e}") from e
