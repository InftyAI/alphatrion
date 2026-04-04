# ruff: noqa: E501
# ruff: noqa: B904

import logging
import uuid
from importlib.metadata import version

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

from alphatrion.server.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from alphatrion.server.graphql.context import get_context
from alphatrion.server.graphql.schema import schema
from alphatrion.storage import runtime

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


# Wrapper to convert context auth errors to HTTP exceptions
async def get_context_with_error_handling(request: Request):
    """Wrap get_context to convert auth errors to proper HTTP status codes."""
    try:
        return await get_context(request)
    except ValueError as e:
        # Authentication/authorization errors from get_context
        error_msg = str(e).lower()
        if (
            "authorization" in error_msg
            or "token" in error_msg
            or "missing" in error_msg
        ):
            raise HTTPException(status_code=401, detail=str(e))
        # Other validation errors
        raise HTTPException(status_code=400, detail=str(e))


# Create GraphQL router with context
graphql_app = GraphQLRouter(schema, context_getter=get_context_with_error_handling)

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


# Auth endpoints
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Authenticate user and return JWT token with user information."""
    try:
        metadb = runtime.storage_runtime().metadb

        # Find user by email
        user = metadb.get_user_by_email(email=credentials.email)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Get user's teams
        team_members = metadb.get_team_members_by_user_id(user_id=user.uuid)
        teams = []
        for member in team_members:
            team = metadb.get_team(team_id=member.team_id)
            if team:
                teams.append(
                    {
                        "id": str(team.uuid),
                        "name": team.name,
                        "description": team.description,
                    }
                )

        # Create JWT token with user claims
        # Note: team_id is NOT included - users can belong to multiple teams
        # Team selection is handled in the UI
        token_data = {
            "sub": str(user.uuid),  # subject = user_id
            "user_id": str(user.uuid),
            "org_id": str(user.org_id),
            "email": user.email,
        }

        access_token = create_access_token(data=token_data)

        # Return token and user info
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.uuid),
                "name": user.name,
                "email": user.email,
                "avatarUrl": user.avatar_url,
                "meta": user.meta,
                "createdAt": user.created_at.isoformat(),
                "updatedAt": user.updated_at.isoformat(),
                "teams": teams,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/auth/change-password")
async def change_password(request: Request, password_data: ChangePasswordRequest):
    """Change user's password."""
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        token = auth_header.replace("Bearer ", "")

        # Decode token to get user_id
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        metadb = runtime.storage_runtime().metadb

        # Get user from database
        user = metadb.get_user(user_id=uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        # Hash new password
        new_password_hash = hash_password(password_data.new_password)

        # Update password in database
        metadb.update_user(user_id=uuid.UUID(user_id), password_hash=new_password_hash)

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
