# ruff: noqa: E501

# test query from graphql endpoint

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from openai import OpenAI

from alphatrion.experiment.craft_experiment import CraftExperiment
from alphatrion.log.log import log_dataset
from alphatrion.runtime.runtime import init
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status
from alphatrion.tracing import tracing


def test_query_single_team(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    query = f"""
    query {{
        team(id: "{test_team_id}") {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalExperiments
            totalRuns
            aggregatedTokens {{
                totalTokens
                inputTokens
                outputTokens
            }}
            expsByTimeframe(startTime: "{yesterday}", endTime: "{tomorrow}") {{
                id
               updatedAt
            }}
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["team"]["id"] == str(test_team_id)
    assert response.data["team"]["name"] == "Test Team"
    assert response.data["team"]["totalExperiments"] == 0
    assert response.data["team"]["totalRuns"] == 0
    assert len(response.data["team"]["expsByTimeframe"]) == 0


def test_query_team_with_experiments(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        name="Test Experiment",
        team_id=test_team_id,
        user_id=test_user_id,
        status=Status.RUNNING,
        meta={},
    )

    _ = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id,
    )
    _ = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id,
    )

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    query = f"""
    query {{
        team(id: "{test_team_id}") {{
            id
            name
            description
            meta
            createdAt
            updatedAt
            totalExperiments
            totalRuns
            expsByTimeframe(startTime: "{yesterday}", endTime: "{tomorrow}") {{
                id
            }}
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert response.data["team"]["totalExperiments"] == 1
    assert response.data["team"]["totalRuns"] == 2
    assert len(response.data["team"]["expsByTimeframe"]) == 1


def test_query_teams(execute_graphql, test_org_id, test_user_id):
    runtime.init()

    metadb = runtime.storage_runtime().metadb
    team1_id = metadb.create_team(
        org_id=test_org_id,
        name="Test Team1",
        description="A team for testing",
        meta={"foo": "bar"},
    )
    team2_id = metadb.create_team(
        org_id=test_org_id,
        name="Test Team2",
        description="Another team for testing",
        meta={"baz": 123},
    )
    user_id = metadb.create_user(
        org_id=test_org_id,
        name="tester",
        email=f"tester-{test_org_id}@inftyai.com",
        meta={"foo": "bar"},
        team_id=team1_id,
    )
    # Add user to team2 as well with a different way.
    metadb.add_user_to_team(user_id=user_id, team_id=team2_id)

    query = """
    query {
        teams {
            id
            name
            description
            meta
            createdAt
            updatedAt
        }
    }
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=user_id,
    )
    assert response.errors is None
    assert len(response.data["teams"]) >= 2


def test_query_user(execute_graphql, test_org_id, test_user_id):
    runtime.init()

    metadb = runtime.storage_runtime().metadb
    team_id = metadb.create_team(
        org_id=test_org_id,
        name="Test Team",
        description="A team for testing",
        meta={"foo": "bar"},
    )

    unique_email = f"tester-{test_org_id}@inftyai.com"
    user_id = metadb.create_user(
        org_id=test_org_id,
        name="tester",
        email=unique_email,
        meta={"foo": "bar"},
    )

    # Add user to team
    metadb.add_user_to_team(user_id=user_id, team_id=team_id)

    query = f"""
    query {{
        user(id: "{user_id}") {{
            id
            name
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
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=user_id,
    )
    assert response.errors is None
    assert response.data["user"]["name"] == "tester"
    assert response.data["user"]["email"] == unique_email
    assert len(response.data["user"]["teams"]) == 1
    assert response.data["user"]["teams"][0]["id"] == str(team_id)
    assert response.data["user"]["meta"] == {"foo": "bar"}


def test_query_single_exp(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        name="Test Experiment",
        team_id=test_team_id,
        user_id=test_user_id,
        status=Status.RUNNING,
        meta={},
    )

    query = f"""
    query {{
        experiment(id: "{exp_id}") {{
            id
            teamId
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
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert "experiment" in response.data
    assert response.data["experiment"]["id"] == str(exp_id)


def test_query_experiments(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()
    metadb = runtime.storage_runtime().metadb
    _ = metadb.create_experiment(
        org_id=test_org_id,
        name="Test Experiment1",
        team_id=test_team_id,
        user_id=test_user_id,
    )
    _ = metadb.create_experiment(
        org_id=test_org_id,
        name="Test Experiment2",
        team_id=test_team_id,
        user_id=test_user_id,
    )

    query = f"""
    query {{
        experiments(teamId: "{test_team_id}", page: 0, pageSize: 10) {{
            id
            teamId
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
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
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
        messages=[
            {
                "role": "user",
                "content": "Tell me a joke about opentelemetry, as short as possible.",
            }
        ],
    )
    print(completion.choices[0].message.content)
    await asyncio.sleep(0.1)  # Simulate some work


@pytest.mark.asyncio
async def test_query_single_run(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    init(team_id=test_team_id, user_id=test_user_id)

    # Verify tracing is actually enabled
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, (
        "TraceStore must be initialized when ALPHATRION_ENABLE_TRACING=true"
    )

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

    query = f"""
    query {{
        run(id: "{run_id}") {{
            id
            teamId
            experimentId
            meta
            status
            createdAt
            aggregatedTokens {{
                totalTokens
                inputTokens
                outputTokens
            }}
            spans {{
                traceId
                spanId
            }}
        }}
    }}
    """

    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )

    assert response.errors is None
    assert response.data["run"]["id"] == str(run_id)
    assert response.data["run"]["teamId"] == str(test_team_id)
    assert response.data["run"]["experimentId"] == str(exp_id)
    assert response.data["run"]["status"] == "COMPLETED"
    assert len(response.data["run"]["spans"]) > 0
    # Verify tokens are fetched from ClickHouse via GraphQL fields
    assert response.data["run"]["aggregatedTokens"]["totalTokens"] is not None
    assert response.data["run"]["aggregatedTokens"]["inputTokens"] is not None
    assert response.data["run"]["aggregatedTokens"]["outputTokens"] is not None

    # Verify tokens are NOT cached in meta anymore
    metadb = runtime.storage_runtime().metadb
    obj = metadb.get_run(run_id=str(run_id))
    assert obj.status == Status.COMPLETED
    assert obj.meta is None


def test_query_runs(execute_graphql, test_org_id, test_user_id, test_team_id):
    runtime.init()
    metadb = runtime.storage_runtime().metadb
    # Create experiment first
    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        name="Test Experiment",
    )
    _ = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id,
    )
    _ = metadb.create_run(
        org_id=test_org_id,
        team_id=test_team_id,
        user_id=test_user_id,
        experiment_id=exp_id,
    )

    query = f"""
    query {{
        runs(experimentId: "{exp_id}", page: 0, pageSize: 10) {{
            id
            teamId
            experimentId
            meta
            status
            createdAt
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert len(response.data["runs"]) == 2


def test_query_experiment_metrics(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    exp_id = metadb.create_experiment(
        org_id=test_org_id,
        name="Test Experiment",
        team_id=test_team_id,
        user_id=test_user_id,
        status=Status.RUNNING,
        meta={},
    )

    _ = metadb.create_metric(
        org_id=test_org_id,
        team_id=test_team_id,
        experiment_id=exp_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
    )
    _ = metadb.create_metric(
        org_id=test_org_id,
        team_id=test_team_id,
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
                experimentId
                runId
                createdAt
            }}
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert len(response.data["experiment"]["metrics"]) == 2
    for metric in response.data["experiment"]["metrics"]:
        assert metric["teamId"] == str(test_team_id)
        assert metric["experimentId"] == str(exp_id)


@pytest.mark.asyncio
async def test_query_experiment_with_usage(
    execute_graphql, test_org_id, test_user_id, test_team_id
):
    init(team_id=test_team_id, user_id=test_user_id)

    exp_id = None

    async with CraftExperiment.start(
        name="integration_test_experiment_resume",
        description="Experiment for integration test resume",
        meta={"experiment_case": "integration_test_resume"},
    ) as exp:
        exp_id = exp.id
        # Although we called create_joke, but it will be cancelled
        # before get the response from the ollama, the spans will be empty.
        exp.run(create_joke)

        exp._on_signal()  # Simulate sending a signal to trigger resume
        await exp.wait()

    query = f"""
    query {{
        experiment(id: "{exp_id}") {{
            id
            status
            aggregatedTokens {{
                totalTokens
                inputTokens
                outputTokens
            }}
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )

    assert response.errors is None
    assert response.data["experiment"]["status"] == "CANCELLED"
    assert response.data["experiment"]["aggregatedTokens"] is not None
    assert response.data["experiment"]["aggregatedTokens"]["totalTokens"] is not None
    assert response.data["experiment"]["aggregatedTokens"]["inputTokens"] is not None
    assert response.data["experiment"]["aggregatedTokens"]["outputTokens"] is not None

    exp_obj = runtime.storage_runtime().metadb.get_experiment(experiment_id=exp.id)
    assert exp_obj.status == Status.CANCELLED
    assert exp_obj.usage is not None
    assert "total_tokens" in exp_obj.usage
    assert "input_tokens" in exp_obj.usage
    assert "output_tokens" in exp_obj.usage

    # resume the experiment
    async with CraftExperiment.start(name="integration_test_experiment_resume") as exp:
        exp_obj = runtime.storage_runtime().metadb.get_experiment(experiment_id=exp.id)
        assert exp_obj.status == Status.RUNNING
        assert exp_obj.usage is None


@pytest.mark.asyncio
async def test_query_datasets(execute_graphql, test_org_id, test_user_id, test_team_id):
    init(team_id=test_team_id, user_id=test_user_id)

    dataset_id = None
    async with CraftExperiment.start(
        name="Test Experiment for Datasets",
        description="Experiment for testing dataset queries",
    ):
        dataset_id = await log_dataset(
            name="test_dataset",
            data_or_path={"foo": "bar"},
        )

    query = f"""
    query {{
        datasets(teamId: "{test_team_id}", page: 0, pageSize: 10) {{
            id
            name
            path
            meta
            teamId
            experimentId
            runId
            createdAt
        }}
    }}
    """
    response = execute_graphql(
        query=query,
        org_id=test_org_id,
        user_id=test_user_id,
    )
    assert response.errors is None
    assert len(response.data["datasets"]) == 1
    dataset = response.data["datasets"][0]
    assert dataset["id"] == str(dataset_id)
    assert dataset["name"] == "test_dataset"
    assert dataset["path"] is not None
