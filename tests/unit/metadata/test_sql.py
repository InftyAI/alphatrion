import uuid

import pytest

from alphatrion.metadata.sql import SQLStore
from alphatrion.metadata.sql_models import TrialStatus


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_exp(db):
    project_id = uuid.uuid4()
    id = db.create_exp("test_exp", project_id, "test description", {"key": "value"})
    exp = db.get_exp(id)
    assert exp is not None
    assert exp.name == "test_exp"
    assert exp.project_id == project_id
    assert exp.description == "test description"
    assert exp.meta == {"key": "value"}
    assert exp.uuid is not None


def test_delete_exp(db):
    id = db.create_exp("test_exp", uuid.uuid4(), "test description", {"key": "value"})
    db.delete_exp(id)
    exp = db.get_exp(id)
    assert exp is None


def test_update_exp(db):
    id = db.create_exp("test_exp", uuid.uuid4(), "test description", {"key": "value"})
    db.update_exp(id, name="new_name")
    exp = db.get_exp(id)
    assert exp.name == "new_name"


def test_list_exps(db):
    project_id1 = uuid.uuid4()
    project_id2 = uuid.uuid4()
    db.create_exp("exp1", project_id1, None, None)
    db.create_exp("exp2", project_id1, None, None)
    db.create_exp("exp3", project_id2, None, None)

    exps = db.list_exps(project_id1, 0, 10)
    assert len(exps) == 2

    exps = db.list_exps(project_id2, 0, 10)
    assert len(exps) == 1

    exps = db.list_exps(uuid.uuid4(), 0, 10)
    assert len(exps) == 0


def test_create_trial(db):
    project_id = uuid.uuid4()
    exp_id = db.create_exp("test_exp", project_id, "test description")
    trial_id = db.create_trial(
        exp_id=exp_id, project_id=project_id, name="test-trial", params={"lr": 0.01}
    )
    trial = db.get_trial(trial_id)
    assert trial is not None
    assert trial.experiment_id == exp_id
    assert trial.name == "test-trial"
    assert trial.status == TrialStatus.PENDING
    assert trial.meta is None
    assert trial.params == {"lr": 0.01}


def test_update_trial(db):
    project_id = uuid.uuid4()
    exp_id = db.create_exp("test_exp", project_id, "test description")
    trial_id = db.create_trial(exp_id=exp_id, project_id=project_id, name="test-trial")
    trial = db.get_trial(trial_id)
    assert trial.status == TrialStatus.PENDING
    assert trial.meta is None

    db.update_trial(trial_id, status=TrialStatus.RUNNING, meta={"note": "started"})
    trial = db.get_trial(trial_id)
    assert trial.status == TrialStatus.RUNNING
    assert trial.meta == {"note": "started"}


def test_create_metric(db):
    project_id = uuid.uuid4()
    exp_id = db.create_exp("test_exp", project_id, "test description")
    trial_id = db.create_trial(exp_id=exp_id, project_id=project_id, name="test-trial")
    run_id = db.create_run(trial_id=trial_id, project_id=project_id)
    db.create_metric(project_id, trial_id, run_id, "accuracy", 0.95, 1)
    db.create_metric(project_id, trial_id, run_id, "accuracy", 0.85, 2)

    metrics = db.list_metrics(trial_id)
    assert len(metrics) == 2
    assert metrics[0].key == "accuracy"
    assert metrics[0].value == 0.95
    assert metrics[1].key == "accuracy"
    assert metrics[1].value == 0.85
