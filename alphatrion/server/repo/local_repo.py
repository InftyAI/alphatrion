import logging
from pathlib import Path

from alphatrion.server.repo.gcs_repo import FileEntry, detect_language

logger = logging.getLogger(__name__)

# Directories and files to skip when building the tree
SKIP_PATTERNS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".idea",
    ".vscode",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.egg-info",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "coverage",
    ".coverage",
    "htmlcov",
}


def should_skip(name: str) -> bool:
    """Check if a file or directory should be skipped."""
    if name in SKIP_PATTERNS:
        return True
    # Check wildcard patterns
    for pattern in SKIP_PATTERNS:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
    return False


class LocalRepoService:
    """Service for accessing local filesystem repositories."""

    _instance: "LocalRepoService | None" = None

    @classmethod
    def get_instance(cls) -> "LocalRepoService":
        """Get singleton instance of LocalRepoService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def path_exists(self, path: str) -> bool:
        """Check if a path exists and is a directory."""
        try:
            p = Path(path)
            return p.exists() and p.is_dir()
        except Exception as e:
            logger.error(f"Error checking path existence for {path}: {e}")
            return False

    def get_file_tree(self, base_path: str, max_depth: int = 10) -> dict | None:
        """
        Get the file tree structure for a local directory.

        Returns a nested dict structure representing the file tree,
        or None if the path doesn't exist.
        """
        try:
            base = Path(base_path).resolve()
            if not base.exists() or not base.is_dir():
                return None

            root = FileEntry(name="", path="", is_dir=True)
            self._build_tree(base, root, base, depth=0, max_depth=max_depth)

            # Sort children alphabetically (directories first)
            self._sort_children(root)

            return root.to_dict()
        except Exception as e:
            logger.error(f"Error building file tree for {base_path}: {e}")
            return None

    def _build_tree(
        self,
        current_path: Path,
        parent: FileEntry,
        base_path: Path,
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursively build the file tree."""
        if depth >= max_depth:
            return

        try:
            entries = sorted(current_path.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            logger.warning(f"Permission denied: {current_path}")
            return
        except Exception as e:
            logger.warning(f"Error reading directory {current_path}: {e}")
            return

        for entry in entries:
            if should_skip(entry.name):
                continue

            # Calculate relative path from base
            try:
                rel_path = str(entry.relative_to(base_path))
            except ValueError:
                rel_path = entry.name

            file_entry = FileEntry(
                name=entry.name, path=rel_path, is_dir=entry.is_dir()
            )

            if parent.children is not None:
                parent.children.append(file_entry)

            if entry.is_dir():
                self._build_tree(entry, file_entry, base_path, depth + 1, max_depth)

    def _sort_children(self, entry: FileEntry) -> None:
        """Sort children alphabetically (directories first)."""
        if entry.children is not None:
            entry.children.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            for child in entry.children:
                self._sort_children(child)

    def get_file_content(self, base_path: str, file_path: str) -> str | None:
        """
        Get the content of a specific file.

        Returns the file content as a string, or None if not found.
        """
        try:
            full_path = Path(base_path) / file_path
            full_path = full_path.resolve()

            # Security check: ensure the file is within the base path
            base = Path(base_path).resolve()
            if not str(full_path).startswith(str(base)):
                logger.warning(f"Path traversal attempt: {file_path}")
                return None

            if not full_path.exists() or not full_path.is_file():
                return None

            # Read file with encoding detection
            try:
                return full_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return full_path.read_text(encoding="latin-1")
        except Exception as e:
            logger.error(f"Error reading file {file_path} from {base_path}: {e}")
            return None

    def get_file_language(self, file_path: str) -> str | None:
        """Detect the programming language based on file extension."""
        return detect_language(file_path)
