# ruff: noqa: E501

# test query from graphql endpoint

import uuid
from datetime import datetime, timedelta

from alphatrion.server.graphql.runtime import graphql_runtime, init
from alphatrion.server.graphql.schema import schema
from alphatrion.storage.sql_models import Status


def test_query_single_team():
    init(init_tables=True)
    metadb = graphql_runtime().metadb
    id = metadb.create_team(name="Test Team", description="A team for testing")

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    query = f"""
    query {{
        team(id: "{id}") {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalProjects
            totalExperiments
            totalRuns
            listExpsByTimeframe(startTime: "{yesterday}", endTime: "{tomorrow}") {{
                id
               updatedAt
            }}
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["team"]["id"] == str(id)
    assert response.data["team"]["name"] == "Test Team"
    assert response.data["team"]["totalProjects"] == 0
    assert response.data["team"]["totalExperiments"] == 0
    assert response.data["team"]["totalRuns"] == 0
    assert len(response.data["team"]["listExpsByTimeframe"]) == 0


def test_query_team_with_experiments():
    user_id = uuid.uuid4()
    init(init_tables=True)
    metadb = graphql_runtime().metadb
    team_id = metadb.create_team(name="Test Team", description="A team for testing")

    project_id = metadb.create_project(
        name="Test Project",
        description="A project for testing",
        team_id=team_id,
        user_id=user_id,
    )

    exp_id = metadb.create_experiment(
        name="Test Experiment",
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        status=Status.RUNNING,
        meta={},
    )

    _ = metadb.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        experiment_id=exp_id,
    )
    _ = metadb.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        experiment_id=exp_id,
    )

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    query = f"""
    query {{
        team(id: "{team_id}") {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalProjects
            totalExperiments
            totalRuns
            listExpsByTimeframe(startTime: "{yesterday}", endTime: "{tomorrow}") {{
                id
            }}
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["team"]["totalProjects"] == 1
    assert response.data["team"]["totalExperiments"] == 1
    assert response.data["team"]["totalRuns"] == 2
    assert len(response.data["team"]["listExpsByTimeframe"]) == 1


def test_query_teams():
    init(init_tables=True)

    metadb = graphql_runtime().metadb
    team1_id = metadb.create_team(
        name="Test Team1", description="A team for testing", meta={"foo": "bar"}
    )
    team2_id = metadb.create_team(
        name="Test Team2", description="Another team for testing", meta={"baz": 123}
    )
    user_id = metadb.create_user(
        username="tester",
        email="example@inftyai.com",
        meta={"foo": "bar"},
        team_id=team1_id,
    )
    # Add user to team2 as well with a different way.
    metadb.add_user_to_team(user_id=user_id, team_id=team2_id)

    query = f"""
    query {{
        teams(userId: "{user_id}") {{
            id
            name
            description
            meta
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["teams"]) >= 2


def test_query_user():
    init(init_tables=True)

    metadb = graphql_runtime().metadb
    team_id = metadb.create_team(
        name="Test Team", description="A team for testing", meta={"foo": "bar"}
    )

    user_id = metadb.create_user(
        username="tester",
        email="tester@inftyai.com",
        meta={"foo": "bar"},
    )

    # Add user to team
    metadb.add_user_to_team(user_id=user_id, team_id=team_id)

    query = f"""
    query {{
        user(id: "{user_id}") {{
            id
            username
            email
            meta
            teams {{
                id
                name
            }}
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["user"]["username"] == "tester"
    assert response.data["user"]["email"] == "tester@inftyai.com"
    assert len(response.data["user"]["teams"]) == 1
    assert response.data["user"]["teams"][0]["id"] == str(team_id)
    assert response.data["user"]["meta"] == {"foo": "bar"}


def test_query_single_project():
    init(init_tables=True)

    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    id = metadb.create_project(
        name="Test Project",
        description="A project for testing",
        team_id=team_id,
        user_id=user_id,
    )

    query = f"""
    query {{
        project(id: "{id}") {{
            id
            teamId
            name
            description
            meta
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["project"]["id"] == str(id)
    assert response.data["project"]["name"] == "Test Project"


def test_query_projects():
    init(init_tables=True)
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = graphql_runtime().metadb

    _ = metadb.create_project(
        name="Test Project1",
        description="A project for testing",
        team_id=team_id,
        user_id=user_id,
    )
    _ = metadb.create_project(
        name="Test Project2",
        description="A project for testing",
        team_id=team_id,
        user_id=user_id,
    )
    _ = metadb.create_project(
        name="Test Project3",
        description="A project for testing",
        team_id=uuid.uuid4(),
        user_id=user_id,
    )

    query = f"""
    query {{
        projects(teamId: "{team_id}", page: 0, pageSize: 10) {{
            id
            teamId
            name
            description
            meta
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["projects"]) == 2


def test_query_single_exp():
    init(init_tables=True)
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    metadb = graphql_runtime().metadb

    exp_id = metadb.create_experiment(
        name="Test Experiment",
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        status=Status.RUNNING,
        meta={},
    )

    query = f"""
    query {{
        experiment(id: "{exp_id}") {{
            id
            teamId
            projectId
            meta
            params
            duration
            status
            kind
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert "experiment" in response.data
    assert response.data["experiment"]["id"] == str(exp_id)
    assert response.data["experiment"]["projectId"] == str(project_id)


def test_query_experiments():
    init(init_tables=True)
    team_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    _ = metadb.create_experiment(
        name="Test Experiment1",
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
    )
    _ = metadb.create_experiment(
        name="Test Experiment2",
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
    )

    query = f"""
    query {{
        experiments(projectId: "{project_id}", page: 0, pageSize: 10) {{
            id
            teamId
            projectId
            name
            description
            params
            duration
            kind
            status
            createdAt
            updatedAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["experiments"]) == 2


def test_query_single_run():
    init(init_tables=True)
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    exp_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    run_id = metadb.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        experiment_id=exp_id,
    )
    response = schema.execute_sync(
        f"""
    query {{
        run(id: "{run_id}") {{
            id
            teamId
            projectId
            experimentId
            meta
            status
            createdAt
        }}
    }}
    """,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["run"]["id"] == str(run_id)
    assert response.data["run"]["teamId"] == str(team_id)
    assert response.data["run"]["projectId"] == str(project_id)
    assert response.data["run"]["experimentId"] == str(exp_id)


def test_query_runs():
    init(init_tables=True)
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    exp_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    _ = metadb.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        experiment_id=exp_id,
    )
    _ = metadb.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=project_id,
        experiment_id=exp_id,
    )

    query = f"""
    query {{
        runs(experimentId: "{exp_id}", page: 0, pageSize: 10) {{
            id
            teamId
            projectId
            experimentId
            meta
            status
            createdAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["runs"]) == 2


def test_query_experiment_metrics():
    init(init_tables=True)
    team_id = uuid.uuid4()
    project_id = uuid.uuid4()
    metadb = graphql_runtime().metadb

    exp_id = metadb.create_experiment(
        name="Test Experiment",
        team_id=team_id,
        user_id=uuid.uuid4(),
        project_id=project_id,
        status=Status.RUNNING,
        meta={},
    )

    _ = metadb.create_metric(
        team_id=team_id,
        project_id=project_id,
        experiment_id=exp_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
    )
    _ = metadb.create_metric(
        team_id=team_id,
        project_id=project_id,
        experiment_id=exp_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
    )
    query = f"""
    query {{
        experiment(id: "{exp_id}") {{
            id
            metrics {{
                id
                key
                value
                teamId
                projectId
                experimentId
                runId
                createdAt
            }}
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["experiment"]["metrics"]) == 2
    for metric in response.data["experiment"]["metrics"]:
        assert metric["teamId"] == str(team_id)
        assert metric["projectId"] == str(project_id)
        assert metric["experimentId"] == str(exp_id)


def test_update_user():
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    user_id = metadb.create_user(
        username="tester",
        email="tester@example.com",
        meta={"foo": "bar"},
    )
    query = f"""
    mutation {{
    updateUser(input: {{
    id: "{user_id}",
    meta: {{"foo": "fuz", "default_team": "team1"}}
    }}){{
        id
        username
        email
        meta
        createdAt
        updatedAt
    }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["updateUser"]["id"] == str(user_id)
    assert response.data["updateUser"]["meta"] == {"foo": "fuz", "default_team": "team1"}
