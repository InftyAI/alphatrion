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
        raise NotImplementedError("list_versions is not implemented for S3 backend")

    def pull(
        self, repo_name: str, version: str, output_dir: str | None = None
    ) -> list[str]:
        raise NotImplementedError("pull is not implemented for S3 backend")

    def delete(self, repo_name: str, versions: str | list[str]):
        raise NotImplementedError("delete is not implemented for S3 backend")

    def generate_download_urls(
        self, path: str, version_id: str | None = None, expires_in: int = 30
    ) -> list[dict[str, str]]:
        """Generate presigned URLs for downloading artifacts from S3 with native versioning.

        :param path: Repository path (e.g., "org_id/team_id/exp_id/repo")
        :param version_id: Optional specific version ID to download. If None, downloads latest versions.
        :param expires_in: URL expiration time in seconds (default: 30 seconds)
        :return: List of dicts with 'filename' and 'url' keys
        """
        try:
            prefix = f"{path}/"

            if version_id:
                # Get specific version
                response = self._s3.list_object_versions(
                    Bucket=self._bucket, Prefix=prefix
                )

                if "Versions" not in response:
                    return []

                download_urls = []
                for obj in response["Versions"]:
                    if obj["VersionId"] == version_id:
                        s3_key = obj["Key"]
                        filename = os.path.basename(s3_key)

                        url = self._s3.generate_presigned_url(
                            "get_object",
                            Params={
                                "Bucket": self._bucket,
                                "Key": s3_key,
                                "VersionId": version_id,
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
