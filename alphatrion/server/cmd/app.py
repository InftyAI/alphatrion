# ruff: noqa: E501
# ruff: noqa: B904

import logging
from importlib.metadata import version

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from alphatrion.server.graphql.schema import schema

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware - allows frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function to extract operation name from query
def extract_operation_name(query: str) -> str:
    """Extract operation name from GraphQL query."""
    import re

    # Try to find operation name in format: query OperationName or mutation OperationName
    match = re.search(r"(query|mutation)\s+(\w+)", query)
    if match:
        return match.group(2)

    # Try to find first field selection (e.g., { getExperiment { ... })
    match = re.search(r"\{\s*(\w+)", query)
    if match:
        return match.group(1)

    return "Anonymous"


# Add middleware to log GraphQL requests
@app.middleware("http")
async def log_graphql_requests(request: Request, call_next):
    """Middleware to log GraphQL requests and responses."""
    operation_name = "Unknown"
    operation_type = "query"

    if request.url.path == "/graphql" and request.method == "POST":
        try:
            # Read and cache the body
            body = await request.body()
            import json

            data = json.loads(body)
            query = data.get("query", "")
            variables = data.get("variables", {})

            # Get operation name from request or extract from query
            operation_name = data.get("operationName")
            if not operation_name:
                operation_name = extract_operation_name(query)

            # Extract operation type (query or mutation)
            if query.strip().startswith("mutation"):
                operation_type = "mutation"

            # Log the GraphQL operation request
            variable_keys = list(variables.keys()) if variables else []
            logger.info(
                f"GraphQL {operation_type}: {operation_name} | Variables: {variable_keys if variable_keys else 'None'}"
            )
            logger.debug(f"GraphQL {operation_type} full query:\n{query}")

            # Create a new request with the cached body
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

        except Exception as e:
            logger.error(f"Failed to log GraphQL request: {e}")

    response = await call_next(request)

    # Log response status for GraphQL operations
    if request.url.path == "/graphql" and request.method == "POST":
        try:
            logger.info(
                f"GraphQL {operation_type} {operation_name} completed | Status: {response.status_code}"
            )
        except Exception as e:
            logger.error(f"Failed to log GraphQL response: {e}")

    return response


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
