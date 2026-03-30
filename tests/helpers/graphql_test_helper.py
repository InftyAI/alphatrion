"""Helper utilities for GraphQL tests with header context."""

import uuid
from typing import Any
from unittest.mock import Mock

from alphatrion.server.graphql.context import GraphQLContext
from alphatrion.server.graphql.schema import schema


def execute_graphql_query(
    query: str,
    org_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    variables: dict[str, Any] | None = None,
):
    """Execute a GraphQL query with proper context headers.

    Args:
        query: GraphQL query string
        org_id: Organization ID
        team_id: Team ID
        user_id: User ID
        variables: Optional query variables

    Returns:
        GraphQL execution result
    """
    # Create mock request
    mock_request = Mock()

    # Create context with IDs
    context = GraphQLContext(
        org_id=str(org_id),
        team_id=str(team_id),
        user_id=str(user_id),
        request=mock_request,
    )

    # Execute query with context
    return schema.execute_sync(
        query,
        variable_values=variables or {},
        context_value=context,
    )


def execute_graphql_mutation(
    mutation: str,
    org_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    variables: dict[str, Any] | None = None,
):
    """Execute a GraphQL mutation with proper context headers.

    Args:
        mutation: GraphQL mutation string
        org_id: Organization ID
        team_id: Team ID
        user_id: User ID
        variables: Optional mutation variables

    Returns:
        GraphQL execution result
    """
    # Mutations use the same execution path as queries
    return execute_graphql_query(mutation, org_id, team_id, user_id, variables)
