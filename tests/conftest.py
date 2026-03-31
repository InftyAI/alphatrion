"""Pytest configuration and fixtures for AlphaTrion tests."""

import uuid
from typing import Any
from unittest.mock import Mock

import pytest

from alphatrion.server.graphql.context import GraphQLContext
from alphatrion.server.graphql.schema import schema
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import MemberRole


@pytest.fixture(scope="function")
def test_org_id() -> uuid.UUID:
    """Generate a test organization ID."""
    return uuid.uuid4()


@pytest.fixture(scope="function")
def test_team_id(test_org_id: uuid.UUID, test_user_id: uuid.UUID) -> uuid.UUID:
    """Create a test team and add test user to it automatically."""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create user first if it doesn't exist (needed for add_user_to_team)
    user = metadb.get_user(user_id=test_user_id)
    if not user:
        metadb.create_user(
            org_id=test_org_id,
            name="Test User",
            email=f"test-{test_user_id}@example.com",
            uuid=test_user_id,
        )

    team_id = metadb.create_team(
        org_id=test_org_id, name="Test Team", description="A team for testing"
    )
    metadb.add_user_to_team(
        user_id=test_user_id, team_id=team_id, role=MemberRole.SUPER_ADMIN
    )

    return team_id


@pytest.fixture(scope="function")
def test_user_id() -> uuid.UUID:
    """Generate a test user ID."""
    return uuid.uuid4()


@pytest.fixture(scope="function")
def graphql_context(test_org_id: uuid.UUID, test_user_id: uuid.UUID) -> GraphQLContext:
    """Provide GraphQL context with test IDs.

    This fixture creates a GraphQLContext with test org_id and user_id.
    Use this when you need to customize the context or pass it explicitly.
    """
    mock_request = Mock()
    return GraphQLContext(
        org_id=str(test_org_id),
        user_id=str(test_user_id),
        request=mock_request,
    )


@pytest.fixture(scope="function")
def execute_graphql():
    """Execute GraphQL queries/mutations with automatic context injection.

    This fixture provides a helper function that automatically creates and injects
    the GraphQL context. Use this for most tests.

    Usage:
        def test_something(execute_graphql):
            response = execute_graphql(
                query="query { team { id } }",
                org_id=org_id,
                user_id=user_id,
            )
            assert response.errors is None
    """

    def _execute(
        query: str,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        variables: dict[str, Any] | None = None,
    ):
        """Execute a GraphQL query with context.

        Args:
            query: GraphQL query or mutation string
            org_id: Organization ID for context
            user_id: User ID for context
            variables: Optional GraphQL variables

        Returns:
            GraphQL execution result
        """
        mock_request = Mock()
        context = GraphQLContext(
            org_id=str(org_id),
            user_id=str(user_id),
            request=mock_request,
        )

        return schema.execute_sync(
            query,
            variable_values=variables or {},
            context_value=context,
        )

    return _execute


@pytest.fixture(scope="function")
def setup_test_team(test_org_id: uuid.UUID, test_user_id: uuid.UUID):
    """Create a test team in the database and add test user to it.

    Returns a function that creates a team with the given name.
    Automatically uses test_org_id and adds test_user_id to the team.

    Usage:
        def test_something(setup_test_team):
            team_id = setup_test_team("My Team")
    """

    def _create_team(
        name: str = "Test Team", description: str = "A test team"
    ) -> uuid.UUID:
        runtime.init()
        metadb = runtime.storage_runtime().metadb

        # Create team
        team_id = metadb.create_team(
            org_id=test_org_id,
            name=name,
            description=description,
        )

        # Add test user to team for permission checks
        metadb.add_user_to_team(
            user_id=test_user_id, team_id=team_id, role=MemberRole.SUPER_ADMIN
        )

        return team_id

    return _create_team
