import io
import logging
import os
import zipfile
from functools import lru_cache

from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class FileEntry:
    """Represents a file or directory entry in the repository."""

    def __init__(self, name: str, path: str, is_dir: bool):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.children: list[FileEntry] | None = [] if is_dir else None

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "path": self.path,
            "is_dir": self.is_dir,
        }
        if self.children is not None:
            result["children"] = [child.to_dict() for child in self.children]
        return result


class GCSRepoService:
    """Service for accessing repository files stored in GCS as zip archives."""

    _instance: "GCSRepoService | None" = None

    def __init__(self, bucket_name: str | None = None):
        default_bucket = "hi-artifacts"
        self.bucket_name = bucket_name or default_bucket
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None
        self._zip_cache: dict[str, zipfile.ZipFile] = {}
        self._zip_bytes_cache: dict[str, bytes] = {}

    @classmethod
    def get_instance(cls) -> "GCSRepoService":
        """Get singleton instance of GCSRepoService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client()
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _get_blob_path(self, trial_id: str) -> str:
        """Get the GCS blob path for a trial's repo zip."""
        return f"repos/{trial_id}.zip"

    def repo_exists(self, trial_id: str) -> bool:
        """Check if a repository zip exists for the given trial."""
        try:
            blob = self.bucket.blob(self._get_blob_path(trial_id))
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking repo existence for trial {trial_id}: {e}")
            return False

    def _get_zip_file(self, trial_id: str) -> zipfile.ZipFile | None:
        """Get or download the zip file for a trial."""
        if trial_id in self._zip_cache:
            return self._zip_cache[trial_id]

        try:
            blob = self.bucket.blob(self._get_blob_path(trial_id))
            zip_bytes = blob.download_as_bytes()
            self._zip_bytes_cache[trial_id] = zip_bytes
            zip_file = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
            self._zip_cache[trial_id] = zip_file
            return zip_file
        except NotFound:
            logger.warning(f"Repo zip not found for trial {trial_id}")
            return None
        except Exception as e:
            logger.error(f"Error downloading repo zip for trial {trial_id}: {e}")
            return None

    def get_file_tree(self, trial_id: str) -> dict | None:
        """
        Get the file tree structure for a trial's repository.

        Returns a nested dict structure representing the file tree,
        or None if the repository doesn't exist.
        """
        zip_file = self._get_zip_file(trial_id)
        if zip_file is None:
            return None

        # Build a tree structure from the zip file contents
        root = FileEntry(name="", path="", is_dir=True)
        dir_map: dict[str, FileEntry] = {"": root}

        # Get all file paths and sort them to process directories first
        file_paths = sorted(zip_file.namelist())

        for file_path in file_paths:
            # Skip empty paths
            if not file_path:
                continue

            # Normalize path (remove trailing slash for directories)
            normalized_path = file_path.rstrip("/")
            is_directory = file_path.endswith("/")

            # Split the path into parts
            parts = normalized_path.split("/")
            file_name = parts[-1]

            # Get or create parent directories
            parent_path = ""
            for i, part in enumerate(parts[:-1]):
                current_path = "/".join(parts[: i + 1])
                if current_path not in dir_map:
                    parent = dir_map.get(parent_path, root)
                    new_dir = FileEntry(name=part, path=current_path, is_dir=True)
                    if parent.children is not None:
                        parent.children.append(new_dir)
                    dir_map[current_path] = new_dir
                parent_path = current_path

            # Add the file/directory entry
            if normalized_path not in dir_map:
                parent = dir_map.get(parent_path, root)
                entry = FileEntry(
                    name=file_name, path=normalized_path, is_dir=is_directory
                )
                if parent.children is not None:
                    parent.children.append(entry)
                if is_directory:
                    dir_map[normalized_path] = entry

        # Sort children alphabetically (directories first)
        def sort_children(entry: FileEntry) -> None:
            if entry.children is not None:
                entry.children.sort(key=lambda x: (not x.is_dir, x.name.lower()))
                for child in entry.children:
                    sort_children(child)

        sort_children(root)

        return root.to_dict()

    def get_file_content(self, trial_id: str, file_path: str) -> str | None:
        """
        Get the content of a specific file from a trial's repository.

        Returns the file content as a string, or None if not found.
        """
        zip_file = self._get_zip_file(trial_id)
        if zip_file is None:
            return None

        try:
            # Try both with and without trailing slash for the path
            try:
                content = zip_file.read(file_path)
            except KeyError:
                # Try without leading slash if present
                if file_path.startswith("/"):
                    content = zip_file.read(file_path[1:])
                else:
                    raise

            # Try to decode as UTF-8, fall back to latin-1
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")
        except KeyError:
            logger.warning(f"File {file_path} not found in repo for trial {trial_id}")
            return None
        except Exception as e:
            logger.error(
                f"Error reading file {file_path} from repo for trial {trial_id}: {e}"
            )
            return None

    def clear_cache(self, trial_id: str | None = None) -> None:
        """Clear the zip file cache for a specific trial or all trials."""
        if trial_id:
            if trial_id in self._zip_cache:
                self._zip_cache[trial_id].close()
                del self._zip_cache[trial_id]
            if trial_id in self._zip_bytes_cache:
                del self._zip_bytes_cache[trial_id]
        else:
            for zf in self._zip_cache.values():
                zf.close()
            self._zip_cache.clear()
            self._zip_bytes_cache.clear()


# Helper function to detect language from file extension
@lru_cache(maxsize=128)
def detect_language(file_path: str) -> str | None:
    """Detect the programming language based on file extension."""
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".cs": "csharp",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "restructuredtext",
        ".r": "r",
        ".R": "r",
        ".lua": "lua",
        ".pl": "perl",
        ".pm": "perl",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hrl": "erlang",
        ".hs": "haskell",
        ".clj": "clojure",
        ".vue": "vue",
        ".svelte": "svelte",
        ".dockerfile": "dockerfile",
        ".tf": "hcl",
        ".proto": "protobuf",
        ".graphql": "graphql",
        ".gql": "graphql",
    }

    _, ext = os.path.splitext(file_path.lower())

    # Special case for Dockerfile without extension
    if file_path.lower().endswith("dockerfile"):
        return "dockerfile"

    return extension_map.get(ext)
