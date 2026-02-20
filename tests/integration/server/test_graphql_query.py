# ruff: noqa: E501

# test query from graphql endpoint

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from openai import OpenAI

from alphatrion import project
from alphatrion.experiment.craft_experiment import CraftExperiment
from alphatrion.runtime.runtime import init
from alphatrion.server.graphql.schema import schema
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status
from alphatrion.tracing import tracing


def test_query_single_team():
    runtime.init()
    metadb = runtime.storage_runtime().metadb
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
    runtime.init()
    metadb = runtime.storage_runtime().metadb
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
    runtime.init()

    metadb = runtime.storage_runtime().metadb
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
    runtime.init()

    metadb = runtime.storage_runtime().metadb
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
    runtime.init()

    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb
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
    runtime.init()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb

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
    runtime.init()
    team_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb
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


client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="",
)


@tracing.workflow()
async def create_joke():
    completion = client.chat.completions.create(
        model="smollm:135m",
        messages=[{"role": "user", "content": "Tell me a joke about opentelemetry"}],
    )
    print(completion.choices[0].message.content)
    await asyncio.sleep(0.1)  # Simulate some work


@pytest.mark.asyncio
async def test_query_single_run():
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    init(team_id=team_id, user_id=user_id)

    # Verify tracing is actually enabled
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, (
        "TraceStore must be initialized when ALPHATRION_ENABLE_TRACING=true"
    )

    async with project.Project.setup(
        name="Test Project", description="A project for testing"
    ) as proj:
        project_id = proj.id
        async with CraftExperiment.start(
            name="Test Experiment",
        ) as exp:
            run = exp.run(create_joke)
            run_id = run.id
            exp_id = exp.id
            await exp.wait()

    # Force flush all spans to ClickHouse
    runtime.storage_runtime().flush()
    # Give ClickHouse time to process the write
    await asyncio.sleep(1)

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
            spans {{
                traceId
                spanId
            }}
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
    assert response.data["run"]["status"] == "COMPLETED"
    assert len(response.data["run"]["spans"]) > 0

    metadb = runtime.storage_runtime().metadb
    obj = metadb.get_run(run_id=str(run_id))
    assert obj.status == Status.COMPLETED
    assert obj.meta["total_tokens"] is not None
    assert obj.meta["input_tokens"] is not None
    assert obj.meta["output_tokens"] is not None


def test_query_runs():
    runtime.init()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    exp_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb
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
    runtime.init()
    team_id = uuid.uuid4()
    project_id = uuid.uuid4()
    metadb = runtime.storage_runtime().metadb

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
