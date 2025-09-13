import os

import oras.client

from alphatrion import consts
from alphatrion.runtime.runtime import Runtime

SUCCESS_CODE = 201


class Artifact:
    def __init__(self, runtime: Runtime, insecure: bool = False):
        self._runtime = runtime
        self._url = os.environ.get(consts.ARTIFACT_REGISTRY_URL)
        self._url = self._url.replace("https://", "").replace("http://", "")
        self._client = oras.client.OrasClient(
            hostname=self._url.strip("/"), auth_backend="token", insecure=insecure
        )

    def push(
        self,
        experiment_name: str,
        files: list[str] | None = None,
        folder: str | None = None,
        version: str = "latest",
    ):
        """
        Push files or all files in a folder to the artifact registry.
        You can specify either files or folder, but not both.
        If both are specified, a ValueError will be raised.

        :param experiment_name: the name of the experiment
        :param files: list of file paths to push
        :param folder: the folder path to push all files in it.
            Don't support nested folders currently.
            Only files in the first level of the folder will be pushed.
        :param version: the version (tag) to push the files under
        """

        if folder and files:
            # Let's be strict here to simplify the implementation.
            raise ValueError("Cannot specify both folder and files.")

        if not folder and not files:
            raise ValueError("Either folder or files must be specified.")

        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._runtime._project_id}/{experiment_name}:{version}"

        files_to_push = files
        if folder:
            if not os.path.isdir(folder):
                raise ValueError(f"{folder} is not a valid directory.")

            os.chdir(folder)
            files_to_push = [f for f in os.listdir(".") if os.path.isfile(f)]

        if not files_to_push:
            raise ValueError("No files to push.")

        try:
            self._client.push(target, files=files_to_push)
        except Exception as e:
            raise RuntimeError("Failed to push artifacts") from e

    def list_versions(self, experiment_name: str) -> list[str]:
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._runtime._project_id}/{experiment_name}"
        try:
            tags = self._client.get_tags(target)
            return tags
        except Exception as e:
            raise RuntimeError("Failed to list artifacts versions") from e

    def delete(self, experiment_name: str, versions: str | list[str]):
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._runtime._project_id}/{experiment_name}"

        try:
            self._client.delete_tags(target, tags=versions)
        except Exception as e:
            raise RuntimeError("Failed to delete artifact versions") from e
