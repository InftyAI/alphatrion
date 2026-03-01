import uuid

import pytest

from alphatrion.storage.sql_models import Status
from alphatrion.storage.sqlstore import SQLStore


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_experiment(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
        params={"lr": 0.01},
    )
    exp = db.get_experiment(exp_id)
    assert exp is not None
    assert exp.name == "test-exp"
    assert exp.status == Status.PENDING
    assert exp.meta is None
    assert exp.params == {"lr": 0.01}


def test_update_experiment(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        team_id=team_id,
        user_id=user_id,
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
    exp_id = db.create_experiment(team_id=team_id, user_id=user_id, name="test-exp")
    run_id = db.create_run(team_id=team_id, user_id=user_id, experiment_id=exp_id)
    db.create_metric(team_id, exp_id, run_id, "accuracy", 0.95)
    db.create_metric(team_id, exp_id, run_id, "loss", 0.1)

    metrics = db.list_metrics_by_experiment_id(exp_id)
    assert len(metrics) == 2
    assert metrics[0].key == "accuracy"
    assert metrics[0].value == 0.95
    assert metrics[1].key == "loss"
    assert metrics[1].value == 0.1


def test_crud_run(db):
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(team_id=team_id, user_id=user_id, name="test-exp")
    run_id = db.create_run(
        team_id=team_id,
        user_id=user_id,
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


def test_create_user_with_team(db):
    team_id = db.create_team(name="Test Team", description="A test team")

    user_id = db.create_user(
        username="tester",
        email="tester@example.com",
        team_id=team_id,
        meta={"role": "engineer", "level": "senior"},
    )
    user = db.get_user(user_id)
    assert user is not None
    assert user.username == "tester"
    assert user.email == "tester@example.com"
    assert user.meta == {"role": "engineer", "level": "senior"}
    teams = db.list_user_teams(user_id)
    assert len(teams) == 1
    assert teams[0].uuid == team_id


def test_create_user_without_team(db):
    user_id = db.create_user(
        username="tester",
        email="tester@example.com",
        meta={"role": "engineer", "level": "senior"},
    )
    user = db.get_user(user_id)
    assert user is not None
    assert user.username == "tester"
    assert user.email == "tester@example.com"
    assert user.meta == {"role": "engineer", "level": "senior"}
    teams = db.list_user_teams(user_id)
    assert len(teams) == 0
