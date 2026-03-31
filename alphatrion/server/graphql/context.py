"""GraphQL context for request-scoped data."""

from fastapi import Request
from strawberry.fastapi import BaseContext


class GraphQLContext(BaseContext):
    """Context object containing request-scoped data extracted from headers."""

    def __init__(self, org_id: str, user_id: str, request: Request):
        super().__init__()
        self.org_id = org_id
        self.user_id = user_id
        self.request = request


async def get_context(request: Request) -> GraphQLContext:
    """Extract org_id, and user_id from request headers.

    Expected headers:
    - x-org-id: Organization ID
    - x-user-id: User ID

    Args:
        request: FastAPI Request object

    Returns:
        GraphQLContext with extracted IDs

    Raises:
        ValueError: If required headers are missing
    """
    org_id = request.headers.get("x-org-id")
    user_id = request.headers.get("x-user-id")

    if not org_id or not user_id:
        missing = []
        if not org_id:
            missing.append("x-org-id")
        if not user_id:
            missing.append("x-user-id")
        raise ValueError(f"Missing required headers: {', '.join(missing)}")

    return GraphQLContext(
        org_id=org_id,
        user_id=user_id,
        request=request,
    )
