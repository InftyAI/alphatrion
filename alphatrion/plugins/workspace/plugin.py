"""
Workspace plugin - AI Studio environment for Alphatrion.

Provides a complete development environment similar to Lightning.ai AI Studio:
- Code editor with syntax highlighting
- File explorer and management
- Integrated terminal
- Jupyter notebook support
- Python environment management
- GPU/resource monitoring
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel

from alphatrion.plugins.base import Plugin, PluginMetadata

# Import K8s modules (optional - will fail gracefully if K8s not configured)
try:
    from alphatrion.plugins.workspace import k8s_pod, k8s_terminal
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    logger.warning("Kubernetes support not available (missing kubernetes library)")

logger = logging.getLogger(__name__)


# API Models
class FileNode(BaseModel):
    """File tree node."""

    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: int | None = None
    modified: float | None = None
    children: list["FileNode"] | None = None


class FileContent(BaseModel):
    """File content."""

    path: str
    content: str
    encoding: str = "utf-8"


class CreateFileRequest(BaseModel):
    """Request to create a file or directory."""

    path: str
    type: str  # 'file' or 'directory'
    content: str | None = None


class RenameRequest(BaseModel):
    """Request to rename a file or directory."""

    old_path: str
    new_path: str


class TerminalCommand(BaseModel):
    """Terminal command to execute."""

    command: str
    cwd: str | None = None


# K8s-specific models
class DeployPodRequest(BaseModel):
    """Request to deploy a K8s pod."""

    name: str
    image: str
    resources: dict | None = None


class K8sFileOperation(BaseModel):
    """K8s file operation request."""

    pod_name: str
    path: str
    content: str | None = None


class WorkspacePlugin(Plugin):
    """
    Cloud IDE plugin provides a full AI development environment.

    Inspired by Lightning.ai AI Studio, this plugin offers:
    - Monaco-based code editor
    - File system browser and editor
    - Integrated terminal
    - Jupyter notebook support
    - Environment management
    - Resource monitoring
    """

    def __init__(self):
        super().__init__()
        self._router: APIRouter | None = None
        self._workspace_root: Path | None = None

    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            id="cloud-ide",
            name="Cloud IDE",
            description="AI development environment with code editor, terminal, and notebooks",
            icon="Code",  # Lucide-react icon
            version="1.0.0",
            author="InftyAI",
            route="/cloud-ide",  # Used by frontend to generate IDE URL
            sidebar_position=5,  # Show near top
            enabled=True,
            open_in_new_tab=True,  # Open in new browser tab
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the Cloud IDE plugin."""
        logger.info("Initializing Cloud IDE plugin")

        # Configure workspace root directory
        workspace_root = config.get("workspace_root") if config else None
        if workspace_root:
            self._workspace_root = Path(workspace_root)
        else:
            # Default to user's home directory or a temp workspace
            self._workspace_root = Path.home() / "alphatrion-workspace"

        # Create workspace directory if it doesn't exist
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace root: {self._workspace_root}")

        # Create API router
        self._router = APIRouter(prefix="/api/plugins/cloud-ide", tags=["cloud-ide"])

        # File System APIs
        @self._router.get("/files/tree")
        async def get_file_tree(path: str = ""):
            """Get file tree structure."""
            try:
                target_path = self._resolve_path(path)
                return self._build_file_tree(target_path)
            except Exception as e:
                logger.error(f"Error getting file tree: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.get("/files/content")
        async def get_file_content(path: str):
            """Read file content."""
            try:
                target_path = self._resolve_path(path)
                if not target_path.is_file():
                    raise HTTPException(status_code=404, detail="File not found")

                content = target_path.read_text(encoding="utf-8")
                return FileContent(path=path, content=content)
            except UnicodeDecodeError:
                # Binary file
                raise HTTPException(
                    status_code=400, detail="Cannot read binary file as text"
                )
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.post("/files/save")
        async def save_file(file_content: FileContent):
            """Save file content."""
            try:
                target_path = self._resolve_path(file_content.path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(file_content.content, encoding="utf-8")
                return {"success": True, "path": file_content.path}
            except Exception as e:
                logger.error(f"Error saving file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.post("/files/create")
        async def create_file(request: CreateFileRequest):
            """Create a new file or directory."""
            try:
                target_path = self._resolve_path(request.path)

                if request.type == "directory":
                    target_path.mkdir(parents=True, exist_ok=True)
                else:  # file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    content = request.content or ""
                    target_path.write_text(content, encoding="utf-8")

                return {"success": True, "path": request.path}
            except Exception as e:
                logger.error(f"Error creating {request.type}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.post("/files/delete")
        async def delete_file(path: str):
            """Delete a file or directory."""
            try:
                target_path = self._resolve_path(path)

                if target_path.is_dir():
                    import shutil

                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()

                return {"success": True, "path": path}
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.post("/files/rename")
        async def rename_file(request: RenameRequest):
            """Rename a file or directory."""
            try:
                old_path = self._resolve_path(request.old_path)
                new_path = self._resolve_path(request.new_path)

                old_path.rename(new_path)
                return {"success": True, "old_path": request.old_path, "new_path": request.new_path}
            except Exception as e:
                logger.error(f"Error renaming file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Terminal APIs
        @self._router.post("/terminal/execute")
        async def execute_command(command: TerminalCommand):
            """Execute a terminal command."""
            try:
                cwd = self._resolve_path(command.cwd) if command.cwd else self._workspace_root

                result = subprocess.run(
                    command.command,
                    shell=True,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=408, detail="Command timed out")
            except Exception as e:
                logger.error(f"Error executing command: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Environment APIs
        @self._router.get("/environment/info")
        async def get_environment_info():
            """Get Python environment information."""
            try:
                import sys
                import platform

                return {
                    "python_version": sys.version,
                    "python_path": sys.executable,
                    "platform": platform.platform(),
                    "architecture": platform.machine(),
                }
            except Exception as e:
                logger.error(f"Error getting environment info: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self._router.get("/environment/packages")
        async def list_packages():
            """List installed Python packages."""
            try:
                result = subprocess.run(
                    ["pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                import json

                packages = json.loads(result.stdout)
                return {"packages": packages}
            except Exception as e:
                logger.error(f"Error listing packages: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Resource monitoring
        @self._router.get("/resources/status")
        async def get_resource_status():
            """Get system resource usage."""
            try:
                import psutil

                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(str(self._workspace_root))

                resources = {
                    "cpu_percent": cpu_percent,
                    "memory_total": memory.total,
                    "memory_used": memory.used,
                    "memory_percent": memory.percent,
                    "disk_total": disk.total,
                    "disk_used": disk.used,
                    "disk_percent": disk.percent,
                }

                # Try to get GPU info if available
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        gpu_lines = result.stdout.strip().split("\n")
                        resources["gpus"] = [
                            {"info": line} for line in gpu_lines if line
                        ]
                except FileNotFoundError:
                    resources["gpus"] = []

                return resources
            except Exception as e:
                logger.error(f"Error getting resource status: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # K8s Sandbox APIs (optional)
        if K8S_AVAILABLE:
            @self._router.get("/k8s/available")
            async def check_k8s_available():
                """Check if K8s is configured and available."""
                try:
                    k8s_pod.load_k8s_config()
                    return {"available": True}
                except Exception as e:
                    return {"available": False, "error": str(e)}

            @self._router.post("/k8s/pods/deploy")
            async def deploy_k8s_pod(request: DeployPodRequest):
                """Deploy a K8s pod for sandbox environment."""
                try:
                    pod_name = k8s_pod.deploy_pod(
                        name=request.name,
                        image=request.image,
                        resources=request.resources,
                    )
                    return {"success": True, "pod_name": pod_name}
                except Exception as e:
                    logger.error(f"Error deploying pod: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.get("/k8s/pods/list")
            async def list_k8s_pods():
                """List all Cloud IDE pods."""
                try:
                    pods = k8s_pod.list_pods()
                    return {"pods": pods}
                except Exception as e:
                    logger.error(f"Error listing pods: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.get("/k8s/pods/{pod_name}/status")
            async def get_k8s_pod_status(pod_name: str):
                """Get pod status."""
                try:
                    status = k8s_pod.get_pod_status(pod_name)
                    return {"pod_name": pod_name, **status}
                except Exception as e:
                    logger.error(f"Error getting pod status: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.delete("/k8s/pods/{pod_name}")
            async def delete_k8s_pod(pod_name: str):
                """Delete a pod."""
                try:
                    deleted = k8s_pod.delete_pod(pod_name)
                    return {"success": True, "deleted": deleted}
                except Exception as e:
                    logger.error(f"Error deleting pod: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.get("/k8s/pods/{pod_name}/files/list")
            async def list_k8s_pod_files(pod_name: str, path: str = "/workspace"):
                """List files in pod directory."""
                try:
                    files = k8s_terminal.list_files(pod_name, path)
                    return {"files": files}
                except Exception as e:
                    logger.error(f"Error listing pod files: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.post("/k8s/pods/{pod_name}/files/read")
            async def read_k8s_pod_file(pod_name: str, request: K8sFileOperation):
                """Read a file from a pod."""
                try:
                    content = k8s_terminal.read_file(pod_name, request.path)
                    return {"success": True, "content": content, "path": request.path}
                except Exception as e:
                    logger.error(f"Error reading pod file: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.post("/k8s/pods/{pod_name}/files/write")
            async def write_k8s_pod_file(pod_name: str, request: K8sFileOperation):
                """Write a file to a pod."""
                try:
                    k8s_terminal.write_file(pod_name, request.path, request.content or "")
                    return {"success": True, "path": request.path}
                except Exception as e:
                    logger.error(f"Error writing pod file: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.post("/k8s/pods/{pod_name}/terminal/execute")
            async def execute_k8s_command(pod_name: str, command: TerminalCommand):
                """Execute a command in a pod."""
                try:
                    result = k8s_terminal.exec_command(pod_name, command.command)
                    return result
                except Exception as e:
                    logger.error(f"Error executing command in pod: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

            @self._router.websocket("/k8s/pods/{pod_name}/terminal")
            async def k8s_terminal_websocket(websocket: WebSocket, pod_name: str):
                """WebSocket endpoint for interactive terminal to a pod."""
                from fastapi import WebSocketDisconnect
                import asyncio

                await websocket.accept()
                exec_stream = None

                try:
                    exec_stream = k8s_terminal.create_exec_stream(pod_name)
                    logger.info(f"K8s terminal session started for pod {pod_name}")

                    async def ws_to_pod():
                        """Forward WebSocket to pod stdin."""
                        try:
                            while exec_stream.is_open():
                                data = await websocket.receive_text()
                                if data:
                                    exec_stream.write_stdin(data)
                        except WebSocketDisconnect:
                            logger.info(f"WebSocket disconnected for pod {pod_name}")
                        except Exception as e:
                            logger.error(f"Error in ws_to_pod: {e}")

                    async def pod_to_ws():
                        """Forward pod stdout/stderr to WebSocket."""
                        try:
                            while exec_stream.is_open():
                                output = exec_stream.read_stdout(timeout=0.1)
                                if output:
                                    await websocket.send_text(output)
                                await asyncio.sleep(0.01)
                        except WebSocketDisconnect:
                            logger.info(f"WebSocket disconnected for pod {pod_name}")
                        except Exception as e:
                            logger.error(f"Error in pod_to_ws: {e}")

                    await asyncio.gather(
                        ws_to_pod(),
                        pod_to_ws(),
                        return_exceptions=True,
                    )

                except Exception as e:
                    logger.error(f"K8s terminal session error: {e}")
                    try:
                        await websocket.send_text(f"\r\nError: {e}\r\n")
                    except Exception:
                        pass
                finally:
                    if exec_stream:
                        try:
                            exec_stream.close()
                        except Exception as e:
                            logger.error(f"Error closing exec stream: {e}")
                    try:
                        await websocket.close()
                    except Exception:
                        pass
                    logger.info(f"K8s terminal session ended for pod {pod_name}")

            logger.info("Cloud IDE plugin initialized with K8s support")
        else:
            logger.info("Cloud IDE plugin initialized (local workspace only)")

        # Serve the IDE HTML page at /plugins/cloud-ide
        from fastapi.responses import FileResponse
        from pathlib import Path as FilePath

        @self._router.get("/ide")
        async def serve_ide():
            """Serve the Cloud IDE HTML page."""
            # Find the dashboard static directory
            current_file = FilePath(__file__).resolve()
            possible_paths = [
                current_file.parents[4] / "dashboard" / "static" / "ide.html",  # Development
                FilePath.cwd() / "dashboard" / "static" / "ide.html",  # From project root
                FilePath.cwd() / "static" / "ide.html",  # From dashboard directory
            ]

            for path in possible_paths:
                if path.exists():
                    return FileResponse(path)

            raise HTTPException(status_code=404, detail="IDE not found. Please build the dashboard first.")

    def get_api_router(self):
        """Return FastAPI router."""
        return self._router

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to workspace root and ensure it's safe.

        Args:
            path: Path string (can be empty for root)

        Returns:
            Resolved absolute Path

        Raises:
            HTTPException: If path tries to escape workspace
        """
        if not path:
            return self._workspace_root

        # Remove leading slash if present
        path = path.lstrip("/")

        # Resolve path relative to workspace root
        target_path = (self._workspace_root / path).resolve()

        # Ensure the path is within workspace root (security check)
        try:
            target_path.relative_to(self._workspace_root)
        except ValueError:
            raise HTTPException(
                status_code=403, detail="Access denied: Path outside workspace"
            )

        return target_path

    def _build_file_tree(self, root_path: Path, max_depth: int = 3, current_depth: int = 0) -> FileNode:
        """
        Build file tree structure.

        Args:
            root_path: Root directory to scan
            max_depth: Maximum depth to traverse
            current_depth: Current depth in recursion

        Returns:
            FileNode representing the tree
        """
        stat = root_path.stat()
        rel_path = root_path.relative_to(self._workspace_root)

        node = FileNode(
            name=root_path.name or "workspace",
            path=str(rel_path) if str(rel_path) != "." else "",
            type="directory" if root_path.is_dir() else "file",
            size=stat.st_size if root_path.is_file() else None,
            modified=stat.st_mtime,
        )

        # Recursively build children for directories
        if root_path.is_dir() and current_depth < max_depth:
            children = []
            try:
                for item in sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                    # Skip hidden files and common excludes
                    if item.name.startswith(".") or item.name in ["__pycache__", "node_modules"]:
                        continue

                    child_node = self._build_file_tree(item, max_depth, current_depth + 1)
                    children.append(child_node)

                node.children = children
            except PermissionError:
                logger.warning(f"Permission denied reading directory: {root_path}")

        return node

    def shutdown(self) -> None:
        """Cleanup when plugin is unregistered."""
        logger.info("Cloud IDE plugin shutdown")
