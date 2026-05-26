import uuid

import pytest

from alphatrion.storage.sql_models import Status
from alphatrion.storage.sqlstore import SQLStore


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_experiment(db):
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        org_id=org_id,
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
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        org_id=org_id,
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
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="test-exp"
    )
    run_id = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id
    )
    db.create_metric(org_id, team_id, exp_id, run_id, "accuracy", 0.95)
    db.create_metric(org_id, team_id, exp_id, run_id, "loss", 0.1)

    metrics = db.list_metrics_by_experiment_id(exp_id)
    assert len(metrics) == 2
    assert metrics[0].key == "accuracy"
    assert metrics[0].value == 0.95
    assert metrics[1].key == "loss"
    assert metrics[1].value == 0.1


def test_crud_run(db):
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="test-exp"
    )
    run_id = db.create_run(
        org_id=org_id,
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
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team", description="A test team")

    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
        team_id=team_id,
        meta={"role": "engineer", "level": "senior"},
    )
    user = db.get_user(user_id)
    assert user is not None
    assert user.name == "tester"
    assert user.email == "tester@example.com"
    assert user.meta == {"role": "engineer", "level": "senior"}
    teams = db.list_user_teams(user_id)
    assert len(teams) == 1
    assert teams[0].uuid == team_id


def test_create_user_without_team(db):
    org_id = uuid.uuid4()
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
        meta={"role": "engineer", "level": "senior"},
    )
    user = db.get_user(user_id)
    assert user is not None
    assert user.name == "tester"
    assert user.email == "tester@example.com"
    assert user.meta == {"role": "engineer", "level": "senior"}
    teams = db.list_user_teams(user_id)
    assert len(teams) == 0


def test_create_metrics_batch(db):
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exp_id = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="test-exp"
    )
    run_id = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id
    )

    # Create multiple metrics at once
    metrics = {"accuracy": 0.95, "loss": 0.1, "precision": 0.92, "recall": 0.88}
    metric_ids = db.create_metrics(org_id, team_id, exp_id, run_id, metrics)

    # Verify all metrics were created
    assert len(metric_ids) == 4

    # Verify metrics can be retrieved
    stored_metrics = db.list_metrics_by_experiment_id(exp_id)
    assert len(stored_metrics) == 4

    # Verify values are correct
    metric_dict = {m.key: m.value for m in stored_metrics}
    assert metric_dict["accuracy"] == 0.95
    assert metric_dict["loss"] == 0.1
    assert metric_dict["precision"] == 0.92
    assert metric_dict["recall"] == 0.88


def test_user_and_team_in_same_org_success(db):
    """Test that user and team in same org returns True"""
    org_id = uuid.uuid4()

    # Create team
    team_id = db.create_team(org_id=org_id, name="Test Team")

    # Create user in same org
    user_id = db.create_user(
        org_id=org_id, name="test_user", email="user@example.com", team_id=team_id
    )

    # Verify user and team are in same org
    assert db.user_and_team_in_same_org(user_id, team_id, org_id) is True


def test_user_and_team_in_same_org_different_orgs(db):
    """Test that user and team in different orgs returns False"""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()

    # Create team in org1
    team_id = db.create_team(org_id=org1_id, name="Team in Org1")

    # Create user in org2 (different org)
    user_id = db.create_user(org_id=org2_id, name="test_user", email="user@example.com")

    # Verify user and team are NOT in same org
    assert db.user_and_team_in_same_org(user_id, team_id, org1_id) is False


def test_user_and_team_in_same_org_nonexistent_team(db):
    """Test that nonexistent team returns False"""
    org_id = uuid.uuid4()

    # Create user
    user_id = db.create_user(org_id=org_id, name="test_user", email="user@example.com")

    # Use nonexistent team ID
    nonexistent_team_id = uuid.uuid4()

    # Verify returns False for nonexistent team
    assert db.user_and_team_in_same_org(user_id, nonexistent_team_id, org_id) is False


def test_user_and_team_in_same_org_nonexistent_user(db):
    """Test that nonexistent user returns False"""
    org_id = uuid.uuid4()

    # Create team
    team_id = db.create_team(org_id=org_id, name="Test Team")

    # Use nonexistent user ID
    nonexistent_user_id = uuid.uuid4()

    # Verify returns False for nonexistent user
    assert db.user_and_team_in_same_org(nonexistent_user_id, team_id, org_id) is False


def test_user_and_team_in_same_org_wrong_target_org(db):
    """Test that wrong target org returns False"""
    org_id = uuid.uuid4()
    wrong_org_id = uuid.uuid4()

    # Create team in org_id
    team_id = db.create_team(org_id=org_id, name="Test Team")

    # Create user in same org
    user_id = db.create_user(
        org_id=org_id, name="test_user", email="user@example.com", team_id=team_id
    )

    # Verify returns False when checking against wrong target org
    assert db.user_and_team_in_same_org(user_id, team_id, wrong_org_id) is False
