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


def test_delete_experiments_basic(db):
    """Test basic batch deletion of experiments"""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create multiple experiments
    exp_id1 = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="exp1"
    )
    exp_id2 = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="exp2"
    )
    exp_id3 = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="exp3"
    )

    # Create some runs for these experiments
    run_id1 = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id1
    )
    run_id2 = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id2
    )

    # Delete two experiments
    deleted_count = db.delete_experiments([exp_id1, exp_id2])
    assert deleted_count == 2

    # Verify experiments are marked as deleted
    exp1 = db.get_experiment(exp_id1)
    exp2 = db.get_experiment(exp_id2)
    exp3 = db.get_experiment(exp_id3)
    assert exp1 is None
    assert exp2 is None
    assert exp3 is not None

    # Verify runs are also marked as deleted
    run1 = db.get_run(run_id1)
    run2 = db.get_run(run_id2)
    assert run1 is None
    assert run2 is None


def test_delete_experiments_pending_status(db):
    """Test that pending experiments are marked as ABORTED when deleted"""

    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create pending experiments
    exp_id1 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="pending_exp1",
        status=Status.PENDING,
    )
    exp_id2 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="pending_exp2",
        status=Status.PENDING,
    )

    # Delete the pending experiments
    deleted_count = db.delete_experiments([exp_id1, exp_id2])
    assert deleted_count == 2

    # Verify experiments are deleted but check status in the database directly
    # (since get_experiment filters out deleted experiments)
    session = db._session()
    from alphatrion.storage.sql_models import Experiment

    exp1 = session.query(Experiment).filter(Experiment.uuid == exp_id1).first()
    exp2 = session.query(Experiment).filter(Experiment.uuid == exp_id2).first()

    assert exp1 is not None
    assert exp1.is_del == 1
    assert exp1.status == Status.ABORTED

    assert exp2 is not None
    assert exp2.is_del == 1
    assert exp2.status == Status.ABORTED

    session.close()


def test_delete_experiments_running_status(db):
    """Test that running experiments are marked as CANCELLED when deleted"""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create running experiments
    exp_id1 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="running_exp1",
        status=Status.RUNNING,
    )
    exp_id2 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="running_exp2",
        status=Status.RUNNING,
    )

    # Delete the running experiments
    deleted_count = db.delete_experiments([exp_id1, exp_id2])
    assert deleted_count == 2

    # Verify experiments are deleted and status is CANCELLED
    session = db._session()
    from alphatrion.storage.sql_models import Experiment

    exp1 = session.query(Experiment).filter(Experiment.uuid == exp_id1).first()
    exp2 = session.query(Experiment).filter(Experiment.uuid == exp_id2).first()

    assert exp1 is not None
    assert exp1.is_del == 1
    assert exp1.status == Status.CANCELLED

    assert exp2 is not None
    assert exp2.is_del == 1
    assert exp2.status == Status.CANCELLED

    session.close()


def test_delete_experiments_mixed_statuses(db):
    """Test deleting experiments with various statuses"""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create experiments with different statuses
    exp_id1 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="pending_exp",
        status=Status.PENDING,
    )
    exp_id2 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="running_exp",
        status=Status.RUNNING,
    )
    exp_id3 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="completed_exp",
        status=Status.COMPLETED,
    )
    exp_id4 = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="failed_exp",
        status=Status.FAILED,
    )

    # Create runs for these experiments
    run_id1 = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id1
    )
    run_id2 = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id2
    )
    run_id3 = db.create_run(
        org_id=org_id, team_id=team_id, user_id=user_id, experiment_id=exp_id3
    )

    # Delete all experiments
    deleted_count = db.delete_experiments([exp_id1, exp_id2, exp_id3, exp_id4])
    assert deleted_count == 4

    # Verify experiments have correct status after deletion
    session = db._session()
    from alphatrion.storage.sql_models import Experiment

    exp1 = session.query(Experiment).filter(Experiment.uuid == exp_id1).first()
    exp2 = session.query(Experiment).filter(Experiment.uuid == exp_id2).first()
    exp3 = session.query(Experiment).filter(Experiment.uuid == exp_id3).first()
    exp4 = session.query(Experiment).filter(Experiment.uuid == exp_id4).first()

    # PENDING -> ABORTED
    assert exp1.is_del == 1
    assert exp1.status == Status.ABORTED

    # RUNNING -> CANCELLED
    assert exp2.is_del == 1
    assert exp2.status == Status.CANCELLED

    # COMPLETED stays COMPLETED
    assert exp3.is_del == 1
    assert exp3.status == Status.COMPLETED

    # FAILED stays FAILED
    assert exp4.is_del == 1
    assert exp4.status == Status.FAILED

    session.close()

    # Verify all runs are marked as deleted
    run1 = db.get_run(run_id1)
    run2 = db.get_run(run_id2)
    run3 = db.get_run(run_id3)
    assert run1 is None
    assert run2 is None
    assert run3 is None


def test_delete_experiments_empty_list(db):
    """Test deleting with empty experiment list"""
    deleted_count = db.delete_experiments([])
    assert deleted_count == 0


def test_delete_experiments_nonexistent_ids(db):
    """Test deleting nonexistent experiments"""
    nonexistent_id1 = uuid.uuid4()
    nonexistent_id2 = uuid.uuid4()

    deleted_count = db.delete_experiments([nonexistent_id1, nonexistent_id2])
    assert deleted_count == 0


def test_delete_experiments_mixed_existing_and_nonexistent(db):
    """Test deleting mix of existing and nonexistent experiments"""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create one experiment
    exp_id1 = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="exp1"
    )
    nonexistent_id = uuid.uuid4()

    # Delete one existing and one nonexistent
    deleted_count = db.delete_experiments([exp_id1, nonexistent_id])
    assert deleted_count == 1

    # Verify the existing one is deleted
    exp1 = db.get_experiment(exp_id1)
    assert exp1 is None


def test_delete_experiments_already_deleted(db):
    """Test deleting experiments that are already deleted"""
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create experiment
    exp_id = db.create_experiment(
        org_id=org_id, team_id=team_id, user_id=user_id, name="exp1"
    )

    # Delete once
    deleted_count = db.delete_experiments([exp_id])
    assert deleted_count == 1

    # Try to delete again
    deleted_count = db.delete_experiments([exp_id])
    assert deleted_count == 0
