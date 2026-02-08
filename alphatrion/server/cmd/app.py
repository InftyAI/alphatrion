# ruff: noqa: E501
# ruff: noqa: B904

import os
from importlib.metadata import version

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from strawberry.fastapi import GraphQLRouter

from alphatrion import envs
from alphatrion.server.graphql.schema import schema

app = FastAPI()

# Add CORS middleware - allows frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Mount /graphql endpoint
app.include_router(graphql_app, prefix="/graphql")


# health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}


# version endpoint
@app.get("/version")
def get_version():
    return {"version": version("alphatrion"), "status": "ok"}


# ORAS Registry Proxy Endpoints
def get_registry_url() -> str:
    """Get the ORAS registry URL from environment variables."""
    registry_url = os.environ.get(envs.ARTIFACT_REGISTRY_URL)
    if not registry_url:
        raise HTTPException(
            status_code=500, detail="ARTIFACT_REGISTRY_URL not configured"
        )
    # Ensure URL has scheme
    if not registry_url.startswith(("http://", "https://")):
        # Default to https if no scheme specified
        registry_url = f"https://{registry_url}"
    return registry_url.rstrip("/")


@app.get("/api/artifacts/repositories")
async def list_repositories():
    """Proxy request to ORAS registry to list all repositories."""
    registry_url = get_registry_url()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{registry_url}/v2/_catalog",
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Registry request failed: {e}")


@app.get("/api/artifacts/repositories/{team}/{project}/tags")
async def list_tags(team: str, project: str):
    """Proxy request to ORAS registry to list tags for a repository."""
    registry_url = get_registry_url()
    repo_path = f"{team}/{project}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{registry_url}/v2/{repo_path}/tags/list",
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to list tags: {e}")


@app.get("/api/artifacts/repositories/{team}/{project}/manifests/{tag}")
async def get_manifest(team: str, project: str, tag: str):
    """Proxy request to ORAS registry to get manifest for a specific tag."""
    registry_url = get_registry_url()
    repo_path = f"{team}/{project}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{registry_url}/v2/{repo_path}/manifests/{tag}",
                headers={
                    "Accept": "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to get manifest: {e}")


@app.get("/api/artifacts/repositories/{team}/{project}/blobs/{digest:path}")
async def get_blob(team: str, project: str, digest: str):
    """Proxy request to ORAS registry to get blob content."""
    registry_url = get_registry_url()
    repo_path = f"{team}/{project}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{registry_url}/v2/{repo_path}/blobs/{digest}",
                timeout=30.0,
            )
            response.raise_for_status()
            # Return raw blob content
            return Response(
                content=response.content,
                media_type=response.headers.get(
                    "content-type", "application/octet-stream"
                ),
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", ""
                    ),
                },
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to get blob: {e}")
