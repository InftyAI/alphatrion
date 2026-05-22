"""Artifact storage client with pluggable backends (OCI or S3)."""

import os

from alphatrion import envs

SUCCESS_CODE = 201

ARTIFACT_TYPE_S3 = "s3"
ARTIFACT_TYPE_OCI = "oci"


class Artifact:
    """Artifact storage client with pluggable backends (OCI or S3)."""

    def __init__(self, insecure: bool = False):
        self._storage_type = os.environ.get(
            envs.ARTIFACT_STORAGE_TYPE, ARTIFACT_TYPE_OCI
        ).lower()

        if self._storage_type == ARTIFACT_TYPE_S3:
            from alphatrion.artifact.s3_backend import S3Backend

            self._backend = S3Backend()
        elif self._storage_type == ARTIFACT_TYPE_OCI:
            from alphatrion.artifact.oci_backend import OCIBackend

            self._backend = OCIBackend(insecure=insecure)
        else:
            raise ValueError(
                f"Unsupported artifact storage type: {self._storage_type}. "
                f"Supported types: '{ARTIFACT_TYPE_OCI}', '{ARTIFACT_TYPE_S3}'"
            )

    @property
    def storage_type(self):
        return self._storage_type

    def push(
        self,
        repo_name: str,
        paths: str | list[str],
        version: str | None = None,
    ) -> str:
        """
        Push files or all files in a folder to the artifact storage.

        :param repo_name: the name of the repository to push to
        :param paths: list of file paths or a folder path to push.
        :param version: the version (tag) to push the files under
        """
        return self._backend.push(repo_name, paths, version)

    def list_versions(self, repo_name: str) -> list[str]:
        """List all versions for a repository."""
        return self._backend.list_versions(repo_name)

    def pull(
        self, repo_name: str, version_or_filename: str, output_dir: str | None = None
    ) -> list[str]:
        """
        Pull artifacts from the storage.

        :param repo_name: the name of the repository to pull from
        :param version_or_filename: the version (tag) or filename to pull.
            For OCI backend, this is always the tag.
            For S3 backend, if this matches a file name under the repo,
            that file will be pulled. Otherwise, if this matches a version folder
            (e.g., "v1"), all files under that folder will be pulled.
        :param output_dir: optional directory to save files to
        :return: list of absolute file paths that were downloaded
        """
        return self._backend.pull(repo_name, version_or_filename, output_dir)

    def delete(self, repo_name: str, versions: str | list[str]):
        """Delete specific versions from a repository."""
        return self._backend.delete(repo_name, versions)


# For backward compatibility
def get_registry_url() -> str:
    """Get the ORAS registry URL from environment variables."""
    from alphatrion.artifact.oci_backend import get_registry_url as _get_registry_url

    return _get_registry_url()
