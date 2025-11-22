# test query from graphql endpoint

import uuid

from alphatrion.graphql.schema import schema
from alphatrion.runtime import runtime
from alphatrion.runtime.runtime import init


def test_query_single_project():
    init(project_id=uuid.uuid4(), init_tables=True)
    metadb = runtime.global_runtime().metadb
    id = metadb.create_project(name="Test Project", description="A project for testing")

    query = f"""
    query {{
        project(id: "{id}") {{
            id
            name
            description
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
    init(project_id=uuid.uuid4(), init_tables=True)
    metadb = runtime.global_runtime().metadb
    _ = metadb.create_project(name="Test Project1", description="A project for testing")
    _ = metadb.create_project(name="Test Project2", description="A project for testing")

    query = """
    query {
        projects {
            id
            name
            description
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
    # Because runtime.global_runtime().metadb may contain projects from other tests
    assert len(response.data["projects"]) == 3


def test_query_single_experiment():
    project_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb
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
    project_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb
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
    project_id = uuid.uuid4()
    experiment_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb

    trial_id = metadb.create_trial(
        name="Test Trial",
        project_id=project_id,
        experiment_id=experiment_id,
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
    project_id = uuid.uuid4()
    experiment_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb
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
    project_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb
    run_id = metadb.create_run(
        project_id=project_id,
        trial_id=trial_id,
    )
    response = schema.execute_sync(
        f"""
    query {{
        run(id: "{run_id}") {{
            id
            trialId
            projectId
            meta
            createdAt
        }}
    }}
    """,
        variable_values={},
    )
    assert response.errors is None
    assert response.data["run"]["id"] == str(run_id)
    assert response.data["run"]["trialId"] == str(trial_id)
    assert response.data["run"]["projectId"] == str(project_id)


def test_query_runs():
    project_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb
    _ = metadb.create_run(
        project_id=project_id,
        trial_id=trial_id,
    )
    _ = metadb.create_run(
        project_id=project_id,
        trial_id=trial_id,
    )

    query = f"""
    query {{
        runs(trialId: "{trial_id}", page: 0, pageSize: 10) {{
            id
            trialId
            meta
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
    project_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    init(project_id=project_id, init_tables=True)
    metadb = runtime.global_runtime().metadb

    _ = metadb.create_metric(
        project_id=project_id,
        trial_id=trial_id,
        run_id=uuid.uuid4(),
        key="accuracy",
        value=0.95,
        step=0,
    )
    _ = metadb.create_metric(
        project_id=project_id,
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
            name
            value
            projectId
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
        assert metric["trialId"] == str(trial_id)
