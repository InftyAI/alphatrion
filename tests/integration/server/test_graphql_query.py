# test query from graphql endpoint

import uuid

from alphatrion.metadata.sql_models import Status
from alphatrion.server.graphql.runtime import graphql_runtime, init
from alphatrion.server.graphql.schema import schema


def test_query_single_project():
    init(init_tables=True)
    metadb = graphql_runtime().metadb
    id = metadb.create_project(name="Test Project", description="A project for testing")

    query = f"""
    query {{
        project(id: "{id}") {{
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
    assert response.data["project"]["id"] == str(id)
    assert response.data["project"]["name"] == "Test Project"


def test_query_projects():
    init(init_tables=True)
    metadb = graphql_runtime().metadb
    _ = metadb.create_project(
        name="Test Project1", description="A project for testing", meta={"foo": "bar"}
    )
    _ = metadb.create_project(
        name="Test Project2", description="A project for testing", meta={"baz": 123}
    )

    query = """
    query {
        projects {
            id
            name
            description
            meta
            createdAt
            updatedAt
        }
    }
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["projects"]) >= 2


def test_query_single_experiment():
    init(init_tables=True)
    project_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    id = metadb.create_exp(
        name="Test Experiment",
        description="A experiment for testing",
        project_id=project_id,
    )

    query = f"""
    query {{
        experiment(id: "{id}") {{
            id
            projectId
            name
            description
            meta
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
    assert response.data["experiment"]["id"] == str(id)
    assert response.data["experiment"]["name"] == "Test Experiment"


def test_query_experiments():
    init(init_tables=True)
    project_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    _ = metadb.create_exp(
        name="Test Experiment1",
        description="A experiment for testing",
        project_id=project_id,
    )
    _ = metadb.create_exp(
        name="Test Experiment2",
        description="A experiment for testing",
        project_id=project_id,
    )
    _ = metadb.create_exp(
        name="Test Experiment2",
        description="A experiment for testing",
        project_id=uuid.uuid4(),
    )

    query = f"""
    query {{
        experiments(projectId: "{project_id}", page: 0, pageSize: 10) {{
            id
            projectId
            name
            description
            meta
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
    assert len(response.data["experiments"]) == 2


def test_query_single_trial():
    init(init_tables=True)
    project_id = uuid.uuid4()
    experiment_id = uuid.uuid4()
    metadb = graphql_runtime().metadb

    trial_id = metadb.create_trial(
        name="Test Trial",
        project_id=project_id,
        experiment_id=experiment_id,
        status=Status.RUNNING,
        meta={},
    )

    query = f"""
    query {{
        trial(id: "{trial_id}") {{
            id
            projectId
            experimentId
            meta
            params
            duration
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
    assert "trial" in response.data
    assert response.data["trial"]["id"] == str(trial_id)
    assert response.data["trial"]["experimentId"] == str(experiment_id)
    assert response.data["trial"]["projectId"] == str(project_id)


def test_query_trials():
    init(init_tables=True)
    project_id = uuid.uuid4()
    experiment_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    _ = metadb.create_trial(
        name="Test Trial1",
        experiment_id=experiment_id,
        project_id=project_id,
    )
    _ = metadb.create_trial(
        name="Test Trial2",
        experiment_id=experiment_id,
        project_id=project_id,
    )

    query = f"""
    query {{
        trials(experimentId: "{experiment_id}", page: 0, pageSize: 10) {{
            id
            projectId
            experimentId
            name
            description
            params
            duration
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
    assert len(response.data["trials"]) == 2


def test_query_single_run():
    init(init_tables=True)
    project_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    exp_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    run_id = metadb.create_run(
        project_id=project_id,
        experiment_id=exp_id,
        trial_id=trial_id,
    )
    response = schema.execute_sync(
        f"""
    query {{
        run(id: "{run_id}") {{
            id
            trialId
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
    assert response.data["run"]["projectId"] == str(project_id)
    assert response.data["run"]["experimentId"] == str(exp_id)
    assert response.data["run"]["trialId"] == str(trial_id)


def test_query_runs():
    init(init_tables=True)
    project_id = uuid.uuid4()
    exp_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    metadb = graphql_runtime().metadb
    _ = metadb.create_run(
        project_id=project_id,
        experiment_id=exp_id,
        trial_id=trial_id,
    )
    _ = metadb.create_run(
        project_id=project_id,
        experiment_id=exp_id,
        trial_id=trial_id,
    )

    query = f"""
    query {{
        runs(trialId: "{trial_id}", page: 0, pageSize: 10) {{
            id
            trialId
            experimentId
            projectId
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


def test_query_trial_metrics():
    init(init_tables=True)
    project_id = uuid.uuid4()
    experiment_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    metadb = graphql_runtime().metadb

    _ = metadb.create_metric(
        project_id=project_id,
        experiment_id=experiment_id,
        trial_id=trial_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
        step=0,
    )
    _ = metadb.create_metric(
        project_id=project_id,
        experiment_id=experiment_id,
        trial_id=trial_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
        step=1,
    )
    query = f"""
    query {{
        trialMetrics(trialId: "{trial_id}") {{
            id
            key
            value
            projectId
            experimentId
            trialId
            runId
            step
            createdAt
        }}
    }}
    """
    response = schema.execute_sync(
        query,
        variable_values={},
    )
    assert response.errors is None
    assert len(response.data["trialMetrics"]) == 2
    for metric in response.data["trialMetrics"]:
        assert metric["projectId"] == str(project_id)
        assert metric["experimentId"] == str(experiment_id)
        assert metric["trialId"] == str(trial_id)
