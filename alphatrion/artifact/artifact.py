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

    def push(self, experiment_name: str, files: list[str], version: str = "latest"):
        url = self._url if self._url.endswith("/") else f"{self._url}/"

        target = f"{url}{self._runtime._project_id}/{experiment_name}:{version}"

        try:
            self._client.push(target, files=files)
        except Exception as e:
            raise RuntimeError("Failed to push artifacts") from e

    def list_tags(self, experiment_name: str) -> list[str]:
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._runtime._project_id}/{experiment_name}"
        try:
            tags = self._client.get_tags(target)
            return tags
        except Exception as e:
            raise RuntimeError("Failed to list artifacts tags") from e

    def delete_tags(self, experiment_name: str, versions: str | list):
        url = self._url if self._url.endswith("/") else f"{self._url}/"
        target = f"{url}{self._runtime._project_id}/{experiment_name}"

        try:
            self._client.delete_tags(target, tags=versions)
        except Exception as e:
            raise RuntimeError("Failed to delete tags") from e
