"""GraphQL context for request-scoped data."""

import os

from fastapi import Request
from strawberry.fastapi import BaseContext

from alphatrion import envs
from alphatrion.server.auth import decode_access_token


class GraphQLContext(BaseContext):
    """Context object containing request-scoped data extracted from JWT or headers."""

    def __init__(self, org_id: str, user_id: str, request: Request):
        super().__init__()
        self.org_id = org_id
        self.user_id = user_id
        self.request = request


async def get_context(request: Request) -> GraphQLContext:
    """Extract org_id and user_id from JWT token or request headers.

    Authentication mode is controlled by ALPHATRION_ENABLE_AUTH environment variable:
    - True: Use JWT authentication (Authorization: Bearer <token>)
    - False: Use direct headers (x-org-id, x-user-id)

    Note: team_id is NOT included in the context as users can belong to multiple teams.
    Team selection is handled at the application level.

    Args:
        request: FastAPI Request object

    Returns:
        GraphQLContext with extracted IDs

    Raises:
        ValueError: If authentication fails or required data is missing
    """
    org_id = None
    user_id = None

    # Check if JWT authentication is enabled
    enable_auth = os.getenv(envs.ENABLE_AUTH, "true").lower() == "true"

    if enable_auth:
        # JWT authentication mode
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if not payload:
            raise ValueError("Invalid or expired JWT token")

        org_id = payload.get("org_id")
        user_id = payload.get("user_id")
    else:
        # Direct headers mode
        org_id = request.headers.get("x-org-id")
        user_id = request.headers.get("x-user-id")

    # Validate required fields
    if not org_id or not user_id:
        missing = []
        if not org_id:
            missing.append("org_id" if enable_auth else "x-org-id")
        if not user_id:
            missing.append("user_id" if enable_auth else "x-user-id")
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    return GraphQLContext(
        org_id=org_id,
        user_id=user_id,
        request=request,
    )
