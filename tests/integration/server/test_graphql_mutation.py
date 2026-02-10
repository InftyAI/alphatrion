# ruff: noqa: E501

# test mutations from graphql endpoint

import uuid

from alphatrion.server.graphql.runtime import graphql_runtime, init
from alphatrion.server.graphql.schema import schema


def unique_username(base: str) -> str:
    """Generate unique username for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}"


def unique_email(base: str) -> str:
    """Generate unique email for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}@example.com"


def test_create_team_mutation():
    """Test creating a team via GraphQL mutation"""
    init(init_tables=True)

    mutation = """
    mutation {
        createTeam(input: {
            name: "Test Team"
            description: "A team created via mutation"
            meta: {foo: "bar", count: 42}
        }) {
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalProjects
            totalExperiments
            totalRuns
        }
    }
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["createTeam"]["name"] == "Test Team"
    assert response.data["createTeam"]["description"] == "A team created via mutation"
    assert response.data["createTeam"]["meta"] == {"foo": "bar", "count": 42}
    assert response.data["createTeam"]["totalProjects"] == 0
    assert response.data["createTeam"]["totalExperiments"] == 0
    assert response.data["createTeam"]["totalRuns"] == 0

    # Verify team was actually created in database
    team_id = uuid.UUID(response.data["createTeam"]["id"])
    metadb = graphql_runtime().metadb
    team = metadb.get_team(team_id=team_id)
    assert team is not None
    assert team.name == "Test Team"


def test_create_user_mutation():
    """Test creating a user via GraphQL mutation"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    username = unique_username("testuser")
    email = unique_email("testuser")

    mutation = f"""
    mutation {{
        createUser(input: {{
            username: "{username}"
            email: "{email}"
            meta: {{role: "engineer", level: "senior"}}
        }}) {{
            id
            username
            email
            meta
            createdAt
            updatedAt
            teams {{
                id
                name
            }}
        }}
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["createUser"]["username"] == username
    assert response.data["createUser"]["email"] == email
    assert response.data["createUser"]["meta"] == {
        "role": "engineer",
        "level": "senior",
    }
    assert response.data["createUser"]["teams"] == []  # No teams yet

    # Verify user was actually created in database
    user_id = uuid.UUID(response.data["createUser"]["id"])
    user = metadb.get_user(user_id=user_id)
    assert user is not None
    assert user.username == username


def test_add_user_to_team_mutation():
    """Test adding a user to a team via mutation"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    # Create a team
    team_id = metadb.create_team(name="Test Team", description="First team")

    # Create a user (without team initially)
    user_id = metadb.create_user(
        username=unique_username("testuser"),
        email=unique_email("test"),
    )

    # Verify user has no teams
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 0

    # Add user to team
    # the return is boolean
    mutation = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{team_id}"
        }})
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["addUserToTeam"] is True

    # Verify user is now in team
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 1
    assert teams[0].uuid == team_id


def test_add_user_to_multiple_teams():
    """Test adding a user to multiple teams"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    # Create two teams
    team1_id = metadb.create_team(name="Team 1")
    team2_id = metadb.create_team(name="Team 2")

    # Create a user
    user_id = metadb.create_user(
        username=unique_username("multiuser"),
        email=unique_email("multi"),
    )

    # Add user to first team
    mutation1 = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{team1_id}"
        }})
    }}
    """
    response1 = schema.execute_sync(mutation1, variable_values={})
    assert response1.errors is None
    assert response1.data["addUserToTeam"] is True

    # Add user to second team
    mutation2 = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{team2_id}"
        }})
    }}
    """
    response2 = schema.execute_sync(mutation2, variable_values={})
    assert response2.errors is None
    assert response2.data["addUserToTeam"] is True

    # Verify user is in both teams
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 2
    team_ids = {t.uuid for t in teams}
    assert team1_id in team_ids
    assert team2_id in team_ids


def test_add_user_to_team_with_invalid_team():
    """Test adding a user to a non-existent team"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    # Create a user
    user_id = metadb.create_user(
        username=unique_username("invalidteamuser"),
        email=unique_email("invalidteam"),
    )

    # Try to add user to non-existent team
    fake_team_id = uuid.uuid4()
    mutation = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{fake_team_id}"
        }})
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is not None
    assert "not found" in str(response.errors[0])


def test_add_user_to_team_with_invalid_user():
    """Test adding a non-existent user to a team"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    # Create a team
    team_id = metadb.create_team(name="Test Team")

    # Try to add non-existent user
    fake_user_id = uuid.uuid4()
    mutation = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{fake_user_id}"
            teamId: "{team_id}"
        }})
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is not None
    assert "not found" in str(response.errors[0])


def test_complete_workflow():
    """Test complete workflow: create team, create user, add user to teams"""
    init(init_tables=True)

    username = unique_username("alice")
    email = unique_email("alice")

    # Step 1: Create first team
    mutation1 = """
    mutation {
        createTeam(input: {
            name: "Engineering Team"
            description: "Engineering department"
        }) {
            id
            name
        }
    }
    """
    response1 = schema.execute_sync(mutation1, variable_values={})
    assert response1.errors is None
    team1_id = response1.data["createTeam"]["id"]

    # Step 2: Create second team
    mutation2 = """
    mutation {
        createTeam(input: {
            name: "Data Science Team"
            description: "Data science department"
        }) {
            id
            name
        }
    }
    """
    response2 = schema.execute_sync(mutation2, variable_values={})
    assert response2.errors is None
    team2_id = response2.data["createTeam"]["id"]

    # Step 3: Create user
    mutation3 = f"""
    mutation {{
        createUser(input: {{
            username: "{username}"
            email: "{email}"
            meta: {{title: "Software Engineer"}}
        }}) {{
            id
            username
            teams {{
                id
            }}
        }}
    }}
    """
    response3 = schema.execute_sync(mutation3, variable_values={})
    assert response3.errors is None
    user_id = response3.data["createUser"]["id"]
    assert len(response3.data["createUser"]["teams"]) == 0

    # Step 4: Add user to first team
    mutation4 = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{team1_id}"
        }})
    }}
    """
    response4 = schema.execute_sync(mutation4, variable_values={})
    assert response4.errors is None
    assert response4.data["addUserToTeam"] is True

    # Step 5: Add user to second team
    mutation5 = f"""
    mutation {{
        addUserToTeam(input: {{
            userId: "{user_id}"
            teamId: "{team2_id}"
        }})
    }}
    """
    response5 = schema.execute_sync(mutation5, variable_values={})
    assert response5.errors is None
    assert response5.data["addUserToTeam"] is True

    # Step 6: Verify via query
    query = f"""
    query {{
        user(id: "{user_id}") {{
            id
            username
            teams {{
                id
                name
            }}
        }}
    }}
    """
    response6 = schema.execute_sync(query, variable_values={})
    assert response6.errors is None
    assert len(response6.data["user"]["teams"]) == 2


def test_remove_user_from_team_mutation():
    """Test removing a user from a team via mutation"""
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    # Create a team
    team_id = metadb.create_team(name="Test Team")

    # Create a user and add to team
    user_id = metadb.create_user(
        username=unique_username("removetest"),
        email=unique_email("removetest"),
        team_id=team_id,
    )

    # Verify user is in team
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 1
    assert teams[0].uuid == team_id

    # Remove user from team
    mutation = f"""
    mutation {{
        removeUserFromTeam(input: {{
            userId: "{user_id}"
            teamId: "{team_id}"
        }})
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["removeUserFromTeam"] is True

    # Verify user is no longer in team
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 0


def test_update_user():
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    user_id = metadb.create_user(
        username="tester",
        email="tester@example.com",
        meta={"foo": "bar"},
    )

    mutation = f"""
    mutation {{
        updateUser(input: {{
            id: "{user_id}"
            meta: {{foo: "fuz", newKey: "newValue"}}
        }}) {{
            id
            username
            email
            meta
        }}
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["updateUser"]["id"] == str(user_id)
    assert response.data["updateUser"]["meta"] == {"foo": "fuz", "newKey": "newValue"}
