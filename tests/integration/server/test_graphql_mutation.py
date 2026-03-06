# ruff: noqa: E501

# test mutations from graphql endpoint

import uuid

from alphatrion.server.graphql.schema import schema
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status


def unique_username(base: str) -> str:
    """Generate unique username for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}"


def unique_email(base: str) -> str:
    """Generate unique email for testing"""
    return f"{base}_{uuid.uuid4().hex[:8]}@example.com"


def test_create_team_mutation():
    """Test creating a team via GraphQL mutation"""
    runtime.init()

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
    assert response.data["createTeam"]["totalExperiments"] == 0
    assert response.data["createTeam"]["totalRuns"] == 0

    # Verify team was actually created in database
    team_id = uuid.UUID(response.data["createTeam"]["id"])
    metadb = runtime.storage_runtime().metadb
    team = metadb.get_team(team_id=team_id)
    assert team is not None
    assert team.name == "Test Team"


def test_create_team_mutation_with_uuid():
    """Test creating a team via GraphQL mutation"""
    runtime.init()
    id = uuid.uuid4()  # Generate a UUID to use for the new team

    mutation = f"""
    mutation {{
        createTeam(input: {{
            id: "{str(id)}"
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
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["createTeam"]["name"] == "Test Team"
    # Verify team was actually created in database
    assert response.data["createTeam"]["id"] == str(
        id
    )  # Verify the returned ID matches the provided UUID


def test_create_user_mutation():
    """Test creating a user via GraphQL mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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


def test_create_user_mutation_with_uuid():
    """Test creating a user via GraphQL mutation"""
    runtime.init()
    id = uuid.uuid4()  # Generate a UUID to use for the new user

    username = unique_username("testuser")
    email = unique_email("testuser")

    mutation = f"""
    mutation {{
        createUser(input: {{
            id: "{str(id)}"
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
    assert response.data["createUser"]["id"] == str(
        id
    )  # Verify the returned ID matches the provided UUID


def test_add_user_to_team_mutation():
    """Test adding a user to a team via mutation"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()

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
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    metadb = runtime.storage_runtime().metadb

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


def test_delete_experiment():
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and experiment
    team_id = metadb.create_team(name="Experiment Team")
    user_id = metadb.create_user(
        username=unique_username("expuser"),
        email=unique_email("expuser"),
        team_id=team_id,
    )
    experiment_id = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment to Delete"
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
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["deleteExperiment"] is True

    # Verify experiment is marked as deleted in database
    deleted_experiment = metadb.get_experiment(experiment_id=experiment_id)
    assert deleted_experiment is None


def test_delete_experiments_batch():
    """Test deleting multiple experiments at once"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="Batch Delete Team")
    user_id = metadb.create_user(
        username=unique_username("batchuser"),
        email=unique_email("batchuser"),
        team_id=team_id,
    )

    # Create multiple experiments
    exp_id_1 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment 1"
    )
    exp_id_2 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment 2"
    )
    exp_id_3 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment 3"
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
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["deleteExperiments"] == 3

    # Verify all experiments are marked as deleted
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_2) is None
    assert metadb.get_experiment(experiment_id=exp_id_3) is None


def test_delete_experiments_partial():
    """Test deleting some valid and some invalid experiment IDs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="Partial Delete Team")
    user_id = metadb.create_user(
        username=unique_username("partialuser"),
        email=unique_email("partialuser"),
        team_id=team_id,
    )

    # Create two experiments
    exp_id_1 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Valid Experiment 1"
    )
    exp_id_2 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Valid Experiment 2"
    )

    # Create a fake experiment ID
    fake_exp_id = uuid.uuid4()

    # Delete experiments (including one that doesn't exist)
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{fake_exp_id}", "{exp_id_2}"])
    }}
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    # Should only delete the 2 valid experiments
    assert response.data["deleteExperiments"] == 2

    # Verify valid experiments are deleted, fake one was ignored
    assert metadb.get_experiment(experiment_id=exp_id_1) is None
    assert metadb.get_experiment(experiment_id=exp_id_2) is None


def test_delete_experiments_empty_list():
    """Test deleting with an empty list of experiment IDs"""
    runtime.init()

    mutation = """
    mutation {
        deleteExperiments(experimentIds: [])
    }
    """
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["deleteExperiments"] == 0


def test_delete_experiments_already_deleted():
    """Test deleting experiments that are already deleted"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="Already Deleted Team")
    user_id = metadb.create_user(
        username=unique_username("deluser"),
        email=unique_email("deluser"),
        team_id=team_id,
    )

    # Create an experiment
    exp_id = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment to Delete Twice"
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
    response = schema.execute_sync(
        mutation,
        variable_values={},
    )
    assert response.errors is None
    # Should return 0 since the experiment is already deleted
    assert response.data["deleteExperiments"] == 0


def test_delete_experiment_deletes_runs():
    """Test that deleting an experiment also deletes its runs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team, user, and experiment
    team_id = metadb.create_team(name="Run Delete Team")
    user_id = metadb.create_user(
        username=unique_username("runuser"),
        email=unique_email("runuser"),
        team_id=team_id,
    )
    experiment_id = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment with Runs"
    )

    # Create some runs for this experiment
    run_id_1 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=experiment_id
    )
    run_id_2 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=experiment_id
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
    response = schema.execute_sync(mutation, variable_values={})
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


def test_delete_experiments_batch_deletes_runs():
    """Test that batch deleting experiments also deletes their runs"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="Batch Run Delete Team")
    user_id = metadb.create_user(
        username=unique_username("batchrunuser"),
        email=unique_email("batchrunuser"),
        team_id=team_id,
    )

    # Create multiple experiments with runs
    exp_id_1 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment 1 with Runs"
    )
    run_1_1 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_1
    )
    run_1_2 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_1
    )

    exp_id_2 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Experiment 2 with Runs"
    )
    run_2_1 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_2
    )
    run_2_2 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_2
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
    response = schema.execute_sync(mutation, variable_values={})
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


def test_delete_running_experiment_fails():
    """Test that deleting a running experiment raises an error"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team, user, and experiment
    team_id = metadb.create_team(name="Running Experiment Team")
    user_id = metadb.create_user(
        username=unique_username("runninguser"),
        email=unique_email("runninguser"),
        team_id=team_id,
    )
    experiment_id = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Running Experiment"
    )

    # Set experiment status to RUNNING
    metadb.update_experiment(experiment_id=experiment_id, status=Status.RUNNING)

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
    response = schema.execute_sync(mutation, variable_values={})

    # Should return an error
    assert response.errors is not None
    assert "Cannot delete a running experiment" in str(response.errors[0])

    # Verify experiment still exists
    exp = metadb.get_experiment(experiment_id=experiment_id)
    assert exp is not None
    assert exp.status == Status.RUNNING


def test_delete_experiments_skips_running():
    """Test that batch delete skips running experiments"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="Mixed Status Team")
    user_id = metadb.create_user(
        username=unique_username("mixeduser"),
        email=unique_email("mixeduser"),
        team_id=team_id,
    )

    # Create multiple experiments with different statuses
    exp_id_1 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Completed Experiment"
    )
    metadb.update_experiment(experiment_id=exp_id_1, status=Status.COMPLETED)

    exp_id_2 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Running Experiment"
    )
    metadb.update_experiment(experiment_id=exp_id_2, status=Status.RUNNING)

    exp_id_3 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Failed Experiment"
    )
    metadb.update_experiment(experiment_id=exp_id_3, status=Status.FAILED)

    # Create runs for all experiments
    run_id_1 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_1
    )
    run_id_2 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_2
    )
    run_id_3 = metadb.create_run(
        team_id=team_id, user_id=user_id, experiment_id=exp_id_3
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
    response = schema.execute_sync(mutation, variable_values={})
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


def test_delete_experiments_all_running():
    """Test that batch delete returns 0 when all experiments are running"""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Create a team and user
    team_id = metadb.create_team(name="All Running Team")
    user_id = metadb.create_user(
        username=unique_username("allrunninguser"),
        email=unique_email("allrunninguser"),
        team_id=team_id,
    )

    # Create multiple running experiments
    exp_id_1 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Running Experiment 1"
    )
    metadb.update_experiment(experiment_id=exp_id_1, status=Status.RUNNING)

    exp_id_2 = metadb.create_experiment(
        team_id=team_id, user_id=user_id, name="Running Experiment 2"
    )
    metadb.update_experiment(experiment_id=exp_id_2, status=Status.RUNNING)

    # Try to batch delete all running experiments
    mutation = f"""
    mutation {{
        deleteExperiments(experimentIds: ["{exp_id_1}", "{exp_id_2}"])
    }}
    """
    response = schema.execute_sync(mutation, variable_values={})
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
