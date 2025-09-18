import pytest

from alphatrion.metadata.sql import SQLStore
from alphatrion.metadata.sql_models import TrialStatus


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_exp(db):
    id = db.create_exp("test_exp", "test_project", "test description", {"key": "value"})
    exp = db.get_exp(id)
    assert exp is not None
    assert exp.name == "test_exp"
    assert exp.project_id == "test_project"
    assert exp.description == "test description"
    assert exp.meta == {"key": "value"}
    assert exp.uuid is not None


def test_delete_exp(db):
    id = db.create_exp("test_exp", "test_project", None, None)
    db.delete_exp(id)
    exp = db.get_exp(id)
    assert exp is None


def test_update_exp(db):
    id = db.create_exp("test_exp", "test_project", None, None)
    db.update_exp(id, name="new_name")
    exp = db.get_exp(id)
    assert exp.name == "new_name"


def test_list_exps(db):
    db.create_exp("exp1", "proj1", None, None)
    db.create_exp("exp2", "proj1", None, None)
    db.create_exp("exp3", "proj2", None, None)

    exps = db.list_exps("proj1", 0, 10)
    assert len(exps) == 2

    exps = db.list_exps("proj2", 0, 10)
    assert len(exps) == 1

    exps = db.list_exps("proj3", 0, 10)
    assert len(exps) == 0


def test_create_trial(db):
    exp_id = 1
    trial_id = db.create_trial(exp_id, "test description", None, params={"lr": 0.01})
    trial = db.get_trial(trial_id)
    assert trial is not None
    assert trial.experiment_id == exp_id
    assert trial.description == "test description"
    assert trial.status == TrialStatus.PENDING
    assert trial.meta is None
    assert trial.params == {"lr": 0.01}


def test_update_trial(db):
    exp_id = 1
    trial_id = db.create_trial(exp_id, "test description", None)
    trial = db.get_trial(trial_id)
    assert trial.status == TrialStatus.PENDING
    assert trial.meta is None

    db.update_trial(trial_id, status=TrialStatus.RUNNING, meta={"note": "started"})
    trial = db.get_trial(trial_id)
    assert trial.status == TrialStatus.RUNNING
    assert trial.meta == {"note": "started"}


def test_create_metric(db):
    trial_id = db.create_trial(1, "test description", None)
    db.create_metric(trial_id, "accuracy", 0.95)
    db.create_metric(trial_id, "accuracy", 0.85)

    metrics = db.list_metrics(trial_id)
    assert len(metrics) == 2
    assert metrics[0].key == "accuracy"
    assert metrics[0].value == 0.95
    assert metrics[1].key == "accuracy"
    assert metrics[1].value == 0.85
