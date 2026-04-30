"""Base interface for artifact storage backends."""

from abc import ABC, abstractmethod


class ArtifactStorageBackend(ABC):
    """Abstract base class for artifact storage backends."""

    @abstractmethod
    def push(
        self,
        repo_name: str,
        paths: str | list[str],
        version: str | None = None,
    ) -> str:
        """Push files to the artifact storage.

        :param repo_name: the name of the repository to push to
        :param paths: list of file paths or a folder path to push
        :param version: the version (tag) to push the files under
        :return: the path in format {repo_name}:{version}
        """
        pass

    @abstractmethod
    def list_versions(self, repo_name: str) -> list[str]:
        """List all versions/tags for a repository.

        :param repo_name: the name of the repository
        :return: list of version tags
        """
        pass

    @abstractmethod
    def pull(
        self, repo_name: str, version: str, output_dir: str | None = None
    ) -> list[str]:
        """Pull artifacts from the storage.

        :param repo_name: the name of the repository to pull from
        :param version: the version (tag) to pull
        :param output_dir: optional directory to save files to
        :return: list of absolute file paths that were downloaded
        """
        pass

    @abstractmethod
    def delete(self, repo_name: str, versions: str | list[str]):
        """Delete specific versions from a repository.

        :param repo_name: the name of the repository
        :param versions: version tag(s) to delete
        """
        pass
