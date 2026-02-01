import uuid

import pytest

from alphatrion.storage.sql_models import Status
from alphatrion.storage.sqlstore import SQLStore


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_project(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    id = db.create_project(
        "test_proj", team_id, user_id, "test description", {"key": "value"}
    )
    proj = db.get_project(id)
    assert proj is not None
    assert proj.name == "test_proj"
    assert proj.team_id == team_id
    assert proj.creator_id == user_id
    assert proj.description == "test description"
    assert proj.meta == {"key": "value"}
    assert proj.uuid is not None


def test_delete_project(db):
    id = db.create_project(
        "test_proj", uuid.uuid4(), uuid.uuid4(), "test description", {"key": "value"}
    )
    db.delete_project(id)
    proj = db.get_project(id)
    assert proj is None


def test_update_project(db):
    id = db.create_project(
        "test_proj", uuid.uuid4(), uuid.uuid4(), "test description", {"key": "value"}
    )
    db.update_project(id, name="new_name")
    proj = db.get_project(id)
    assert proj.name == "new_name"


def test_list_projects(db):
    team_id1 = uuid.uuid4()
    team_id2 = uuid.uuid4()
    user_id = uuid.uuid4()
    db.create_project("proj1", team_id1, user_id, None, None)
    db.create_project("proj2", team_id1, user_id, None, None)
    db.create_project("proj3", team_id2, user_id, None, None)

    projs = db.list_projects(team_id1, 0, 10)
    assert len(projs) == 2

    projs = db.list_projects(team_id2, 0, 10)
    assert len(projs) == 1

    projs = db.list_projects(uuid.uuid4(), 0, 10)
    assert len(projs) == 0


def test_create_experiment(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = db.create_project(
        "test_proj", team_id, user_id, "test description", {"key": "value"}
    )
    exp_id = db.create_experiment(
        team_id=team_id,
        user_id=user_id,
        project_id=proj_id,
        name="test-exp",
        params={"lr": 0.01},
    )
    exp = db.get_experiment(exp_id)
    assert exp is not None
    assert exp.project_id == proj_id
    assert exp.name == "test-exp"
    assert exp.status == Status.PENDING
    assert exp.meta is None
    assert exp.params == {"lr": 0.01}


def test_update_experiment(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = db.create_project("test_proj", team_id, user_id, "test description")
    exp_id = db.create_experiment(
        team_id=team_id,
        user_id=user_id,
        project_id=proj_id,
        name="test_exp",
        description="test description",
    )
    exp = db.get_experiment(exp_id)
    assert exp.status == Status.PENDING
    assert exp.meta is None

    db.update_experiment(exp_id, status=Status.RUNNING, meta={"note": "started"})
    exp = db.get_experiment(exp_id)
    assert exp.status == Status.RUNNING
    assert exp.meta == {"note": "started"}


def test_create_metric(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = db.create_project(
        "test_proj", team_id, user_id, "test description", {"key": "value"}
    )
    exp_id = db.create_experiment(
        team_id=team_id, user_id=user_id, project_id=proj_id, name="test-exp"
    )
    run_id = db.create_run(
        team_id=team_id, user_id=user_id, project_id=proj_id, experiment_id=exp_id
    )
    db.create_metric(team_id, proj_id, exp_id, run_id, "accuracy", 0.95)
    db.create_metric(team_id, proj_id, exp_id, run_id, "loss", 0.1)

    metrics = db.list_metrics_by_experiment_id(exp_id)
    assert len(metrics) == 2
    assert metrics[0].key == "accuracy"
    assert metrics[0].value == 0.95
    assert metrics[1].key == "loss"
    assert metrics[1].value == 0.1


def test_crud_run(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = db.create_project(
        "test_proj", team_id, user_id, "test description", {"key": "value"}
    )
    exp_id = db.create_experiment(
        team_id=team_id, user_id=user_id, project_id=proj_id, name="test-exp"
    )
    run_id = db.create_run(
        team_id=team_id,
        user_id=user_id,
        project_id=proj_id,
        experiment_id=exp_id,
        meta={"foo": "bar"},
    )
    run = db.get_run(run_id)
    assert run is not None
    assert run.experiment_id == exp_id
    assert run.status == Status.PENDING

    db.update_run(run_id, status=Status.COMPLETED, meta={"result": "success"})
    run = db.get_run(run_id)
    assert run.status == Status.COMPLETED
    assert run.meta == {"foo": "bar", "result": "success"}
