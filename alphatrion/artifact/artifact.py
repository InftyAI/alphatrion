from http.client import NOT_FOUND
import os
from tkinter import E
from xml.dom import NotFoundErr

import oras.client

from alphatrion import envs
from alphatrion.utils import time as utiltime

SUCCESS_CODE = 201


class Artifact:
    def __init__(self, team_id: str, insecure: bool = False):
        self._team_id = team_id
        self._url = get_registry_url()
        self._client = oras.client.OrasClient(
            hostname=self._url.strip("/"), auth_backend="token", insecure=insecure
        )

    def push(
        self,
        repo_name: str,
        paths: str | list[str],
        version: str | None = None,
    ) -> str:
        """
        Push files or all files in a folder to the artifact registry.
        You can specify either files or folder, but not both.
        If both are specified, a ValueError will be raised.

        :param repo_name: the name of the repository to push to
        :param paths: list of file paths or a folder path to push.
        :param version: the version (tag) to push the files under
        """

        if paths is None or not paths:
            raise ValueError("no files specified to push")

        if isinstance(paths, str):
            if os.path.isdir(paths):
                os.chdir(paths)
                files_to_push = [f for f in os.listdir(".") if os.path.isfile(f)]
            else:
                files_to_push = [paths]
        else:
            files_to_push = paths

        if not files_to_push:
            raise ValueError("No files to push.")

        if version is None:
            version = utiltime.now_2_hash()

        path = f"{self._team_id}/{repo_name}:{version}"
        target = f"{self._url}/{path}"

        try:
            self._client.push(target, files=files_to_push, disable_path_validation=True)
        except Exception as e:
            raise RuntimeError("Failed to push artifacts") from e

        return path

    def list_versions(self, repo_name: str) -> list[str]:
        target = f"{self._url}/{self._team_id}/{repo_name}"
        try:
            tags = self._client.get_tags(target)
            return tags
        except Exception as e:
            # Check if it's a "not found" error (404, repository doesn't exist)
            # TODO: it's not a proper way but let's do it for now.
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg or "does not exist" in error_msg:
                # Return empty list if repository doesn't exist yet
                # This is expected for projects without artifacts
                return []
            # Re-raise other errors
            raise RuntimeError(f"Failed to list artifacts versions: {e}") from e

    def pull(self, repo_name: str, version: str, output_dir: str | None = None) -> list[str]:
        """
        Pull artifacts from the registry.

        :param repo_name: the name of the repository to pull from
        :param version: the version (tag) to pull
        :param output_dir: optional directory to save files to (defaults to current directory)
        :return: list of file paths that were downloaded
        """
        path = f"{self._team_id}/{repo_name}:{version}"
        target = f"{self._url}/{path}"

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            original_dir = os.getcwd()
            os.chdir(output_dir)

        try:
            files = self._client.pull(target)
            return files
        except Exception as e:
            raise RuntimeError(f"Failed to pull artifacts: {e}") from e
        finally:
            if output_dir:
                os.chdir(original_dir)

    def delete(self, repo_name: str, versions: str | list[str]):
        target = f"{self._url}/{self._team_id}/{repo_name}"

        try:
            self._client.delete_tags(target, tags=versions)
        except Exception as e:
            raise RuntimeError("Failed to delete artifact versions") from e

def get_registry_url() -> str:
    """Get the ORAS registry URL from environment variables."""
    registry_url = os.environ.get(envs.ARTIFACT_REGISTRY_URL)
    if not registry_url:
        raise RuntimeError("ARTIFACT_REGISTRY_URL not configured")
    # Ensure URL has scheme
    if not registry_url.startswith(("http://", "https://")):
        registry_url = f"http://{registry_url}"
    return registry_url.rstrip("/")