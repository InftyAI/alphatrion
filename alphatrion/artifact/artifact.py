import os

import oras.client

from alphatrion import consts

SUCCESS_CODE = 201


class Artifact:
    def __init__(self, project_id: str, insecure: bool = False):
        self._project_id = project_id
        self._url = os.environ.get(consts.ARTIFACT_REGISTRY_URL)
        self._url = self._url.replace("https://", "").replace("http://", "")
        self._client = oras.client.OrasClient(
            hostname=self._url.strip("/"), auth_backend="token", insecure=insecure
        )

    def push(
        self,
        repo_name: str,
        paths: str | list[str],
        version: str = "latest",
    ):
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

        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._project_id}/{repo_name}:{version}"

        try:
            self._client.push(target, files=files_to_push)
        except Exception as e:
            raise RuntimeError("Failed to push artifacts") from e

    # TODO: should we store it in the metadb instead?
    def list_versions(self, repo_name: str) -> list[str]:
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._project_id}/{repo_name}"
        try:
            tags = self._client.get_tags(target)
            return tags
        except Exception as e:
            raise RuntimeError("Failed to list artifacts versions") from e

    def delete(self, repo_name: str, versions: str | list[str]):
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._project_id}/{repo_name}"

        try:
            self._client.delete_tags(target, tags=versions)
        except Exception as e:
            raise RuntimeError("Failed to delete artifact versions") from e
