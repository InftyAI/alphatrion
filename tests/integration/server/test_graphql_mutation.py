# ruff: noqa: E501

# test mutations from graphql endpoint

import uuid

from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status


def unique_username(base: str) -> str:
    """Generate unique username for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}"


def unique_email(base: str) -> str:
    """Generate unique email for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}@example.com"


def test_create_team_mutation(execute_graphql, test_org_id, test_user_id, test_team_id):
    """Test creating a team via GraphQL mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    mutation = f"""
    mutation {{
        createTeam(input: {{
            orgId: "{test_org_id}"
            name: "Test Team"
            description: "A team created via mutation"
            meta: {{foo: "bar", count: 42}}
        }}) {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalExperiments
            totalRuns
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["createTeam"]["name"] == "Test Team"
    assert response.data["createTeam"]["description"] == "A team created via mutation"
    assert response.data["createTeam"]["meta"] == {"foo": "bar", "count": 42}
    assert response.data["createTeam"]["totalExperiments"] == 0
    assert response.data["createTeam"]["totalRuns"] == 0

    # Verify team was actually created in database
    new_team_id = uuid.UUID(response.data["createTeam"]["id"])
    team = metadb.get_team(team_id=new_team_id)
    assert team is not None
    assert team.name == "Test Team"


def test_create_team_mutation_with_uuid(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test creating a team via GraphQL mutation"""
    runtime.init()
    id = uuid.uuid4()  # Generate a UUID to use for the new team

    mutation = f"""
    mutation {{
        createTeam(input: {{
            id: "{str(id)}"
            orgId: "{test_org_id}"
            name: "Test Team"
            description: "A team created via mutation"
            meta: {{foo: "bar", count: 42}}
        }}) {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalExperiments
            totalRuns
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["createTeam"]["name"] == "Test Team"
    # Verify team was actually created in database
    assert response.data["createTeam"]["id"] == str(
        id
    )  # Verify the returned ID matches the provided UUID


def test_create_user_mutation(execute_graphql, test_org_id, test_user_id, test_team_id):
    """Test creating a user via GraphQL mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    username = unique_username("testuser")
    email = unique_email("testuser")

    mutation = f"""
    mutation {{
        createUser(input: {{
            orgId: "{test_org_id}"
            name: "{username}"
            email: "{email}"
            meta: {{role: "engineer", level: "senior"}}
        }}) {{
            id
            name
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
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["createUser"]["name"] == username
    assert response.data["createUser"]["email"] == email
    assert response.data["createUser"]["meta"] == {
        "role": "engineer",
        "level": "senior",
    }
    assert response.data["createUser"]["teams"] == []  # No teams yet

    # Verify user was actually created in database
    new_user_id = uuid.UUID(response.data["createUser"]["id"])
    user = metadb.get_user(user_id=new_user_id)
    assert user is not None
    assert user.name == username


def test_create_user_mutation_with_uuid(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test creating a user via GraphQL mutation"""
    runtime.init()
    id = uuid.uuid4()  # Generate a UUID to use for the new user

    username = unique_username("testuser")
    email = unique_email("testuser")

    mutation = f"""
    mutation {{
        createUser(input: {{
            id: "{str(id)}"
            orgId: "{test_org_id}"
            name: "{username}"
            email: "{email}"
            meta: {{role: "engineer", level: "senior"}}
        }}) {{
            id
            name
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
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["createUser"]["id"] == str(
        id
    )  # Verify the returned ID matches the provided UUID


def test_add_user_to_team_mutation(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test adding a user to a team via mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a user (without team initially)
    user_id = metadb.create_user(
        org_id=test_org_id,
        name=unique_username("testuser"),
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
            teamId: "{test_team_id}"
        }})
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["addUserToTeam"] is True

    # Verify user is now in team
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 1
    assert teams[0].uuid == test_team_id


def test_add_user_to_multiple_teams(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test adding a user to multiple teams"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create two teams
    team1_id = metadb.create_team(org_id=test_org_id, name="Team 1")
    team2_id = metadb.create_team(org_id=test_org_id, name="Team 2")

    # Create a user
    user_id = metadb.create_user(
        org_id=test_org_id,
        name=unique_username("multiuser"),
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
    response1 = execute_graphql(
        query=mutation1,
        org_id=test_org_id,
        user_id=test_user_id,
    )
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
    response2 = execute_graphql(
        query=mutation2,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response2.errors is None
    assert response2.data["addUserToTeam"] is True

    # Verify user is in both teams
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 2
    team_ids = {t.uuid for t in teams}
    assert team1_id in team_ids
    assert team2_id in team_ids


def test_add_user_to_team_with_invalid_team(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test adding a user to a non-existent team"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a user
    user_id = metadb.create_user(
        org_id=test_org_id,
        name=unique_username("invalidteamuser"),
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
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is not None
    assert "not found" in str(response.errors[0])


def test_add_user_to_team_with_invalid_user(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test adding a non-existent user to a team"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team
    team_id = metadb.create_team(org_id=test_org_id, name="Test Team")

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
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is not None
    assert "not found" in str(response.errors[0])


def test_user_workflow(execute_graphql, test_org_id, test_user_id, test_team_id):
    """Test user workflow: create team, create user, add user to teams"""
    runtime.init()

    username = unique_username("alice")
    email = unique_email("alice")

    # Step 1: Create first team
    mutation1 = f"""
    mutation {{
        createTeam(input: {{
            orgId: "{test_org_id}"
            name: "Engineering Team"
            description: "Engineering department"
        }}) {{
            id
            name
        }}
    }}
    """
    response1 = execute_graphql(
        query=mutation1,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response1.errors is None
    team1_id = response1.data["createTeam"]["id"]

    # Step 2: Create second team
    mutation2 = f"""
    mutation {{
        createTeam(input: {{
            orgId: "{test_org_id}"
            name: "Data Science Team"
            description: "Data science department"
        }}) {{
            id
            name
        }}
    }}
    """
    response2 = execute_graphql(
        query=mutation2,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response2.errors is None
    team2_id = response2.data["createTeam"]["id"]

    # Step 3: Create user
    mutation3 = f"""
    mutation {{
        createUser(input: {{
            orgId: "{test_org_id}"
            name: "{username}"
            email: "{email}"
            meta: {{title: "Software Engineer"}}
        }}) {{
            id
            name
            teams {{
                id
            }}
        }}
    }}
    """
    response3 = execute_graphql(
        query=mutation3,
        org_id=test_org_id,
        user_id=test_user_id,
    )
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
    response4 = execute_graphql(
        query=mutation4,
        org_id=test_org_id,
        user_id=test_user_id,
    )
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
    response5 = execute_graphql(
        query=mutation5,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response5.errors is None
    assert response5.data["addUserToTeam"] is True

    # Step 6: Verify via query
    query = f"""
    query {{
        user(id: "{user_id}") {{
            id
            name
            teams {{
                id
                name
            }}
        }}
    }}
    """
    response6 = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response6.errors is None
    assert len(response6.data["user"]["teams"]) == 2


def test_remove_user_from_team_mutation(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test removing a user from a team via mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team
    team_id = metadb.create_team(org_id=test_org_id, name="Test Team")

    # Create a user and add to team
    user_id = metadb.create_user(
        org_id=test_org_id,
        name=unique_username("removetest"),
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
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["removeUserFromTeam"] is True

    # Verify user is no longer in team
    teams = metadb.list_user_teams(user_id=user_id)
    assert len(teams) == 0


def test_update_user(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Use unique email for test isolation
    unique_email_str = f"tester_{uuid.uuid4().hex[:8]}@example.com"
    user_id = metadb.create_user(
        org_id=test_org_id,
        name="tester",
        email=unique_email_str,
        meta={"foo": "bar"},
    )

    mutation = f"""
    mutation {{
        updateUser(input: {{
            id: "{user_id}"
            meta: {{foo: "fuz", newKey: "newValue"}}
        }}) {{
            id
            name
            email
            meta
        }}
    }}
    """
    # User can only update themselves, so use the created user_id as context
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=user_id,
    )
    assert response.errors is None
    assert response.data["updateUser"]["id"] == str(user_id)
    assert response.data["updateUser"]["meta"] == {"foo": "fuz", "newKey": "newValue"}


def test_delete_experiment(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    experiment_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment to Delete",
    )

    # Verify experiment exists
    experiment = metadb.get_experiment(experiment_id=experiment_id)
    assert experiment is not None
    assert experiment.name == "Experiment to Delete"

    # Delete experiment via mutation
    mutation = f"""
    mutation {{
        deleteExperiment(experimentId: "{experiment_id}")
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["deleteExperiment"] is True

    # Verify experiment is marked as deleted in database
    deleted_experiment = metadb.get_experiment(experiment_id=experiment_id)
    assert deleted_experiment is None


def test_delete_experiments_batch(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test deleting multiple experiments at once"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create multiple experiments
    exp_id_1 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment 1",
    )
    exp_id_2 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment 2",
    )
    exp_id_3 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment 3",
    )

    # Verify all experiments exist
    assert metadb.get_experiment(experiment_id=exp_id_1) is not None
    assert metadb.get_experiment(experiment_id=exp_id_2) is not None
    assert metadb.get_experiment(experiment_id=exp_id_3) is not None

    # Delete multiple experiments via batch mutation
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{exp_id_2}", "{exp_id_3}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["deleteExperiments"] == 3

    # Verify all experiments are marked as deleted
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_2) is None
    assert metadb.get_experiment(experiment_id=exp_id_3) is None


def test_delete_experiments_partial(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test deleting some valid and some invalid experiment IDs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create two experiments
    exp_id_1 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Valid Experiment 1",
    )
    exp_id_2 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Valid Experiment 2",
    )

    # Create a fake experiment ID
    fake_exp_id = uuid.uuid4()

    # Delete experiments (including one that doesn't exist)
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{fake_exp_id}", "{exp_id_2}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    # Should only delete the 2 valid experiments
    assert response.data["deleteExperiments"] == 2

    # Verify valid experiments are deleted, fake one was ignored
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_2) is None


def test_delete_experiments_empty_list(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test deleting with an empty list of experiment IDs"""
    runtime.init()

    mutation = """
    mutation {
        deleteExperiments(experimentIds: [])
    }
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["deleteExperiments"] == 0


def test_delete_experiments_already_deleted(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test deleting experiments that are already deleted"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create an experiment
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment to Delete Twice",
    )

    # Delete it once
    metadb.delete_experiment(experiment_id=exp_id)
    assert metadb.get_experiment(experiment_id=exp_id) is None

    # Try to delete it again via batch mutation
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    # Should return 0 since the experiment is already deleted
    assert response.data["deleteExperiments"] == 0


def test_delete_experiment_deletes_runs(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that deleting an experiment also deletes its runs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    experiment_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment with Runs",
    )

    # Create some runs for this experiment
    run_id_1 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=experiment_id,
    )
    run_id_2 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=experiment_id,
    )

    # Verify runs exist
    run_1 = metadb.get_run(run_id=run_id_1)
    run_2 = metadb.get_run(run_id=run_id_2)
    assert run_1 is not None
    assert run_2 is not None

    # Delete experiment via mutation
    mutation = f"""
    mutation {{
        deleteExperiment(experimentId: "{experiment_id}")
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["deleteExperiment"] is True

    # Verify experiment is deleted
    deleted_experiment = metadb.get_experiment(experiment_id=experiment_id)
    assert deleted_experiment is None

    # Verify runs are also deleted
    deleted_run_1 = metadb.get_run(run_id=run_id_1)
    deleted_run_2 = metadb.get_run(run_id=run_id_2)
    assert deleted_run_1 is None
    assert deleted_run_2 is None


def test_delete_experiments_batch_deletes_runs(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that batch deleting experiments also deletes their runs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create multiple experiments with runs
    exp_id_1 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment 1 with Runs",
    )
    run_1_1 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_1,
    )
    run_1_2 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_1,
    )

    exp_id_2 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Experiment 2 with Runs",
    )
    run_2_1 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_2,
    )
    run_2_2 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_2,
    )

    # Verify all runs exist
    assert metadb.get_run(run_id=run_1_1) is not None
    assert metadb.get_run(run_id=run_1_2) is not None
    assert metadb.get_run(run_id=run_2_1) is not None
    assert metadb.get_run(run_id=run_2_2) is not None

    # Batch delete experiments
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{exp_id_2}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["deleteExperiments"] == 2

    # Verify experiments are deleted
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_2) is None

    # Verify all runs are also deleted
    assert metadb.get_run(run_id=run_1_1) is None
    assert metadb.get_run(run_id=run_1_2) is None
    assert metadb.get_run(run_id=run_2_1) is None
    assert metadb.get_run(run_id=run_2_2) is None


def test_delete_running_experiment_fails(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that deleting a running experiment raises an error"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    experiment_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Running Experiment",
    )

    # Set experiment status to RUNNING
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=experiment_id,
        status=Status.RUNNING,
    )

    # Verify experiment is running
    exp = metadb.get_experiment(experiment_id=experiment_id)
    assert exp is not None
    assert exp.status == Status.RUNNING

    # Try to delete running experiment via mutation
    mutation = f"""
    mutation {{
        deleteExperiment(experimentId: "{experiment_id}")
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )

    # Should return an error
    assert response.errors is not None
    assert "Cannot delete a running experiment" in str(response.errors[0])

    # Verify experiment still exists
    exp = metadb.get_experiment(experiment_id=experiment_id)
    assert exp is not None
    assert exp.status == Status.RUNNING


def test_delete_experiments_skips_running(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that batch delete skips running experiments"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create multiple experiments with different statuses
    exp_id_1 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Completed Experiment",
    )
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id_1,
        status=Status.COMPLETED,
    )

    exp_id_2 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Running Experiment",
    )
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id_2,
        status=Status.RUNNING,
    )

    exp_id_3 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Failed Experiment",
    )
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id_3,
        status=Status.FAILED,
    )

    # Create runs for all experiments
    run_id_1 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_1,
    )
    run_id_2 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_2,
    )
    run_id_3 = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id_3,
    )

    # Verify all experiments exist
    assert metadb.get_experiment(experiment_id=exp_id_1) is not None
    assert metadb.get_experiment(experiment_id=exp_id_2) is not None
    assert metadb.get_experiment(experiment_id=exp_id_3) is not None

    # Try to batch delete all experiments
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{exp_id_2}", "{exp_id_3}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    # Should only delete 2 experiments (skipped the running one)
    assert response.data["deleteExperiments"] == 2

    # Verify running experiment still exists
    exp_2 = metadb.get_experiment(experiment_id=exp_id_2)
    assert exp_2 is not None
    assert exp_2.status == Status.RUNNING

    # Verify non-running experiments are deleted
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_3) is None

    # Verify runs of deleted experiments are also deleted
    assert metadb.get_run(run_id=run_id_1) is None
    assert metadb.get_run(run_id=run_id_3) is None

    # Verify run of running experiment still exists
    run_2 = metadb.get_run(run_id=run_id_2)
    assert run_2 is not None


def test_delete_experiments_all_running(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that batch delete returns 0 when all experiments are running"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create multiple running experiments
    exp_id_1 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Running Experiment 1",
    )
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id_1,
        status=Status.RUNNING,
    )

    exp_id_2 = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Running Experiment 2",
    )
    metadb.update_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id_2,
        status=Status.RUNNING,
    )

    # Try to batch delete all running experiments
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{exp_id_2}"])
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    # Should delete 0 experiments (all are running)
    assert response.data["deleteExperiments"] == 0

    # Verify all experiments still exist
    exp_1 = metadb.get_experiment(experiment_id=exp_id_1)
    exp_2 = metadb.get_experiment(experiment_id=exp_id_2)
    assert exp_1 is not None
    assert exp_2 is not None
    assert exp_1.status == Status.RUNNING
    assert exp_2.status == Status.RUNNING


def test_create_experiment_mutation(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test creating an experiment via GraphQL mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    mutation = f"""
    mutation {{
        createExperiment(input: {{
            name: "Test Experiment"
            teamId: "{test_team_id}"
            description: "An experiment created via mutation"
            tags: ["ml", "training"]
            meta: {{model: "gpt-4", version: "1.0"}}
            params: {{learningRate: 0.001, batchSize: 32}}
        }}) {{
            id
            name
            description
            status
            kind
            meta
            params
            tags
            createdAt
            updatedAt
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["createExperiment"]["name"] == "Test Experiment"
    assert (
        response.data["createExperiment"]["description"]
        == "An experiment created via mutation"
    )
    assert response.data["createExperiment"]["status"] == "PENDING"
    assert response.data["createExperiment"]["kind"] == "CRAFT_EXPERIMENT"
    assert response.data["createExperiment"]["meta"] == {
        "model": "gpt-4",
        "version": "1.0",
    }
    assert response.data["createExperiment"]["params"] == {
        "learningRate": 0.001,
        "batchSize": 32,
    }
    assert response.data["createExperiment"]["tags"] == ["ml", "training"]

    # Verify experiment was actually created in database
    new_exp_id = uuid.UUID(response.data["createExperiment"]["id"])
    exp = metadb.get_experiment(experiment_id=new_exp_id)
    assert exp is not None
    assert exp.name == "Test Experiment"
    assert exp.status == Status.PENDING


def test_create_experiment_duplicate_name(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that creating an experiment with duplicate name fails"""
    runtime.init()

    # Create first experiment
    mutation1 = f"""
    mutation {{
        createExperiment(input: {{
            name: "Duplicate Name Test"
            teamId: "{test_team_id}"
            description: "First experiment"
        }}) {{
            id
            name
        }}
    }}
    """
    response1 = execute_graphql(
        query=mutation1,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response1.errors is None
    assert response1.data["createExperiment"]["name"] == "Duplicate Name Test"

    # Try to create second experiment with same name
    mutation2 = f"""
    mutation {{
        createExperiment(input: {{
            name: "Duplicate Name Test"
            teamId: "{test_team_id}"
            description: "Second experiment with same name"
        }}) {{
            id
            name
        }}
    }}
    """
    response2 = execute_graphql(
        query=mutation2,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    # Should return an error
    assert response2.errors is not None
    assert "already exists" in str(response2.errors[0])


def test_update_experiment_mutation(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test updating an experiment via GraphQL mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create an experiment first
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Original Name",
        description="Original description",
        meta={"key1": "value1"},
        params={"param1": 1},
    )

    # Update the experiment
    mutation = f"""
    mutation {{
        updateExperiment(input: {{
            id: "{exp_id}"
            description: "Updated description"
            meta: {{key2: "value2"}}
            params: {{param2: 2}}
        }}) {{
            id
            name
            description
            meta
            params
            status
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert (
        response.data["updateExperiment"]["name"] == "Original Name"
    )  # Name should not change
    assert response.data["updateExperiment"]["description"] == "Updated description"
    assert response.data["updateExperiment"]["meta"] == {
        "key1": "value1",
        "key2": "value2",
    }
    assert response.data["updateExperiment"]["params"] == {"param2": 2}

    # Verify in database
    exp = metadb.get_experiment(experiment_id=exp_id)
    assert exp is not None
    assert exp.name == "Original Name"  # Name should remain unchanged
    assert exp.description == "Updated description"


def test_update_experiment_labels_and_tags(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test updating experiment labels and tags"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create an experiment with labels and tags
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Labels Tags Test",
        labels="env:dev,version:1.0",
        tags=["ml", "training"],
    )

    # Update labels and tags
    mutation = f"""
    mutation {{
        updateExperiment(input: {{
            id: "{exp_id}"
            labels: "env:prod,version:2.0"
            tags: ["deep-learning", "testing"]
        }}) {{
            id
            labels {{
                name
                value
            }}
            tags
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert len(response.data["updateExperiment"]["labels"]) == 2
    assert response.data["updateExperiment"]["tags"] == ["deep-learning", "testing"]

    # Verify old labels/tags are replaced
    labels = metadb.list_labels_by_exp_id(exp_id)
    assert len(labels) == 2
    label_dict = {label.label_name: label.label_value for label in labels}
    assert label_dict["env"] == "prod"
    assert label_dict["version"] == "2.0"


def test_update_experiment_not_found(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test updating a non-existent experiment when user has team access"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Ensure the test user is in the test team
    # This way permission check will pass, and we'll get "not found" error
    metadb.add_user_to_team(user_id=test_user_id, team_id=test_team_id)

    fake_exp_id = uuid.uuid4()
    mutation = f"""
    mutation {{
        updateExperiment(input: {{
            id: "{fake_exp_id}"
            description: "New Description"
        }}) {{
            id
            description
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is not None
    # experiment not found in the experiment_is_accessible_to_user
    assert "not allowed to update experiment" in str(response.errors[0]).lower()


def test_abort_experiment_pending(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test aborting a pending experiment"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a pending experiment
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Pending Experiment",
        status=Status.PENDING,
    )

    # Abort the experiment
    mutation = f"""
    mutation {{
        abortExperiment(experimentId: "{exp_id}") {{
            id
            name
            status
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["abortExperiment"]["status"] == "ABORTED"

    # Verify in database
    exp = metadb.get_experiment(experiment_id=exp_id)
    assert exp.status == Status.ABORTED


def test_abort_experiment_running_fails(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that aborting a running experiment fails"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create an experiment and set it to running
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Running Experiment",
    )
    metadb.update_experiment(
        experiment_id=exp_id,
        status=Status.RUNNING,
    )

    # Try to abort the running experiment
    mutation = f"""
    mutation {{
        abortExperiment(experimentId: "{exp_id}") {{
            id
            status
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    # Should return an error
    assert response.errors is not None
    assert "Cannot abort" in str(response.errors[0])

    # Verify status is still RUNNING
    exp = metadb.get_experiment(experiment_id=exp_id)
    assert exp.status == Status.RUNNING


def test_abort_experiment_completed_fails(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test that aborting a completed experiment fails"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create an experiment and set it to completed
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Completed Experiment",
    )
    metadb.update_experiment(
        experiment_id=exp_id,
        status=Status.COMPLETED,
    )

    # Try to abort the completed experiment
    mutation = f"""
    mutation {{
        abortExperiment(experimentId: "{exp_id}") {{
            id
            status
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    # Should return an error
    assert response.errors is not None
    assert "Cannot abort" in str(response.errors[0])

    # Verify status is still COMPLETED
    exp = metadb.get_experiment(experiment_id=exp_id)
    assert exp.status == Status.COMPLETED


def test_abort_experiment_not_found(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    """Test aborting a non-existent experiment when user has team access"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Ensure the test user is in the test team
    # This way permission check will pass, and we'll get "not found" error
    metadb.add_user_to_team(user_id=test_user_id, team_id=test_team_id)

    fake_exp_id = uuid.uuid4()
    mutation = f"""
    mutation {{
        abortExperiment(experimentId: "{fake_exp_id}") {{
            id
            status
        }}
    }}
    """
    response = execute_graphql(
        query=mutation,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is not None
    # experiment not found in the experiment_is_accessible_to_user
    assert "not allowed to abort experiment" in str(response.errors[0]).lower()
