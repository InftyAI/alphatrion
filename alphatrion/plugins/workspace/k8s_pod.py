"""Kubernetes pod management for Cloud IDE sandbox environments."""

import base64
import json
import logging
import os
import tempfile
from http import HTTPStatus
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# HTTP status codes
HTTP_CONFLICT = HTTPStatus.CONFLICT
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND

DEFAULT_NAMESPACE = "default"
DEFAULT_RESOURCES = {
    "requests": {"cpu": "100m", "memory": "256Mi"},
    "limits": {"cpu": "2", "memory": "4Gi"},
}


def _load_gke_config(endpoint: str, ca_b64: str):
    """Configure K8s client for GKE using Google default credentials."""
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())

    ca_data = base64.b64decode(ca_b64)
    ca_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
    ca_file.write(ca_data)
    ca_file.close()

    configuration = client.Configuration()
    configuration.host = f"https://{endpoint}"
    configuration.ssl_ca_cert = ca_file.name
    configuration.api_key = {"authorization": f"Bearer {credentials.token}"}
    client.Configuration.set_default(configuration)


def load_k8s_config():
    """Load K8s config from kubeconfig, GKE env vars, or in-cluster config."""
    kubeconfig = os.environ.get("K8S_KUBECONFIG")
    if kubeconfig:
        config.load_kube_config(config_file=kubeconfig)
        return

    gke_endpoint = os.environ.get("GKE_CLUSTER_ENDPOINT")
    gke_ca = os.environ.get("GKE_CLUSTER_CA")
    if gke_endpoint and gke_ca:
        _load_gke_config(gke_endpoint, gke_ca)
        return

    default_kubeconfig = os.path.expanduser("~/.kube/config")
    if os.path.exists(default_kubeconfig):
        config.load_kube_config(config_file=default_kubeconfig)
        return

    try:
        config.load_incluster_config()
    except config.ConfigException as exc:
        raise RuntimeError(
            "Could not load K8s config. Set K8S_KUBECONFIG, "
            "GKE_CLUSTER_ENDPOINT+GKE_CLUSTER_CA, ensure "
            "~/.kube/config exists, or run inside a K8s cluster."
        ) from exc


def get_namespace() -> str:
    """Get the K8s namespace to use."""
    return os.environ.get("K8S_NAMESPACE", DEFAULT_NAMESPACE)


def deploy_pod(name: str, image: str, resources: dict | None = None) -> str:
    """
    Deploy a pod for Cloud IDE sandbox.

    Args:
        name: Base name for the pod
        image: Docker image to run
        resources: Optional resource requests/limits

    Returns:
        The full pod name
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    sanitized = "".join(
        c if c.isalnum() or c == "-" else "-" for c in name.lower()
    )
    sanitized = sanitized[:40]
    pod_name = f"cloud-ide-{sanitized}"

    res = {
        "requests": dict(DEFAULT_RESOURCES["requests"]),
        "limits": dict(DEFAULT_RESOURCES["limits"]),
    }
    if resources:
        if "requests" in resources:
            res["requests"].update(resources["requests"])
        if "limits" in resources:
            res["limits"].update(resources["limits"])

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            labels={"app": pod_name, "purpose": "cloud-ide"},
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="workspace",
                    image=image,
                    ports=[client.V1ContainerPort(container_port=8080)],
                    resources=client.V1ResourceRequirements(
                        requests=res["requests"],
                        limits=res["limits"],
                    ),
                )
            ],
            restart_policy="Never",
        ),
    )

    try:
        v1.create_namespaced_pod(namespace, pod)
        logger.info(f"Created pod {pod_name} in namespace {namespace}")
    except ApiException as e:
        if e.status == HTTP_CONFLICT:
            logger.info(f"Pod {pod_name} already exists")
        else:
            raise

    return pod_name


def get_pod_status(pod_name: str) -> dict[str, Any]:
    """
    Get pod status.

    Returns:
        Dict with phase, ready boolean, status string, and optional error
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        pod = v1.read_namespaced_pod(pod_name, namespace)
        phase = pod.status.phase

        containers_running = False
        container_error = None

        if pod.status.container_statuses:
            error_reasons = {"CrashLoopBackOff", "ImagePullBackOff"}
            running_count = 0

            for cs in pod.status.container_statuses:
                if not cs.state:
                    continue
                if cs.state.running:
                    running_count += 1
                elif cs.state.waiting and cs.state.waiting.reason in error_reasons:
                    container_error = cs.state.waiting.reason
                elif cs.state.terminated and cs.state.terminated.exit_code != 0:
                    container_error = f"Exit code {cs.state.terminated.exit_code}"

            containers_running = running_count == len(pod.status.container_statuses)

        if container_error:
            status = "failed"
        elif phase == "Running" and containers_running:
            status = "ready"
        elif phase in ("Failed", "Succeeded"):
            status = phase.lower()
        else:
            status = phase.lower()

        return {
            "phase": phase,
            "ready": containers_running,
            "status": status,
            "error": container_error,
        }

    except ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            return {
                "phase": "NotFound",
                "ready": False,
                "status": "not_found",
            }
        raise


def delete_pod(pod_name: str) -> bool:
    """
    Delete a pod.

    Returns:
        True if deleted, False if not found
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        v1.delete_namespaced_pod(pod_name, namespace)
        logger.info(f"Deleted pod {pod_name}")
        return True
    except ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            logger.info(f"Pod {pod_name} not found")
            return False
        raise


def list_pods() -> list[dict[str, Any]]:
    """
    List all Cloud IDE pods in the namespace.

    Returns:
        List of pod info dicts
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    namespace = get_namespace()

    try:
        pods = v1.list_namespaced_pod(
            namespace,
            label_selector="purpose=cloud-ide"
        )

        result = []
        for pod in pods.items:
            pod_info = get_pod_status(pod.metadata.name)
            pod_info["name"] = pod.metadata.name
            pod_info["created_at"] = pod.metadata.creation_timestamp.isoformat()
            result.append(pod_info)

        return result
    except ApiException as e:
        logger.error(f"Error listing pods: {e}")
        return []
