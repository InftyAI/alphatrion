"""Kubernetes terminal and file operations for Cloud IDE."""

import base64
import logging

from kubernetes import client
from kubernetes.stream import stream

from alphatrion.plugins.workspace.k8s_pod import get_namespace, load_k8s_config

logger = logging.getLogger(__name__)


def exec_command(pod_name: str, command: str) -> dict:
    """
    Execute a command in a pod.

    Args:
        pod_name: Name of the pod
        command: Shell command to execute

    Returns:
        Dict with stdout, stderr, and returncode
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container="workspace",
            command=["/bin/sh", "-c", command],
            stdin=False,
            stdout=True,
            stderr=True,
            tty=False,
        )

        # Simple command execution - no returncode easily available
        # Treat any response as success
        return {
            "stdout": resp if resp else "",
            "stderr": "",
            "returncode": 0,
        }
    except Exception as e:
        logger.error(f"Error executing command in pod: {e}")
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": 1,
        }


def read_file(pod_name: str, file_path: str) -> str:
    """
    Read a file from a pod.

    Args:
        pod_name: Name of the pod
        file_path: Path to the file in the pod

    Returns:
        File content as string
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container="workspace",
            command=["cat", file_path],
            stdin=False,
            stdout=True,
            stderr=True,
            tty=False,
        )
        return resp if resp else ""
    except Exception as e:
        logger.error(f"Error reading file from pod: {e}")
        raise RuntimeError(f"Failed to read file: {e}")


def write_file(pod_name: str, file_path: str, content: str) -> bool:
    """
    Write a file to a pod.

    Args:
        pod_name: Name of the pod
        file_path: Path to the file in the pod
        content: File content

    Returns:
        True if successful
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        # Base64 encode for safe transfer
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

        # Write file using base64 decoding
        command = (
            f"mkdir -p \"$(dirname '{file_path}')\" && "
            f"printf '%s' '{encoded}' | base64 -d > '{file_path}'"
        )

        stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container="workspace",
            command=["/bin/sh", "-c", command],
            stdin=False,
            stdout=True,
            stderr=True,
            tty=False,
        )

        logger.info(f"Wrote file {file_path} to pod {pod_name}")
        return True
    except Exception as e:
        logger.error(f"Error writing file to pod: {e}")
        raise RuntimeError(f"Failed to write file: {e}")


def list_files(pod_name: str, dir_path: str = "/workspace") -> list[dict]:
    """
    List files in a directory in the pod.

    Args:
        pod_name: Name of the pod
        dir_path: Directory path in the pod

    Returns:
        List of file info dicts
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        # Use ls -la to get file info
        command = f"ls -la '{dir_path}' 2>/dev/null || echo ''"

        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container="workspace",
            command=["/bin/sh", "-c", command],
            stdin=False,
            stdout=True,
            stderr=True,
            tty=False,
        )

        if not resp:
            return []

        # Parse ls output
        files = []
        for line in resp.strip().split("\n"):
            if not line or line.startswith("total"):
                continue

            parts = line.split()
            if len(parts) < 9:
                continue

            # Parse ls -la format
            permissions = parts[0]
            size = parts[4]
            name = " ".join(parts[8:])

            if name in (".", ".."):
                continue

            file_type = "directory" if permissions.startswith("d") else "file"

            files.append({
                "name": name,
                "type": file_type,
                "size": int(size) if size.isdigit() else 0,
                "path": f"{dir_path.rstrip('/')}/{name}",
            })

        return files
    except Exception as e:
        logger.error(f"Error listing files in pod: {e}")
        return []


def create_exec_stream(pod_name: str):
    """
    Create an interactive terminal stream to a pod.

    Returns:
        Stream object with write_stdin, read_stdout, is_open, close methods
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    logger.info(f"Creating terminal stream to pod {pod_name}")

    exec_stream = stream(
        v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        container="workspace",
        command=[
            "/bin/sh", "-c",
            "export TERM=xterm-256color; "
            "if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi",
        ],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
        _preload_content=False,
    )

    return exec_stream
