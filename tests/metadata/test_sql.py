import pytest
from alphatrion.metadata.sql import SQLStore
from alphatrion.metadata.sql_models import ExperimentStatus


@pytest.fixture
def db():
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_create_exp(db):
    db.create_exp("test_exp", "test_project", "test description", {"key": "value"})
    exp = db.get_exp(1)
    assert exp is not None
    assert exp.name == "test_exp"
    assert exp.project_id == "test_project"
    assert exp.description == "test description"
    assert exp.meta == {"key": "value"}


def test_delete_exp(db):
    db.create_exp("test_exp", "test_project", None, None)
    db.delete_exp(1)
    exp = db.get_exp(1)
    assert exp is None


def test_update_exp(db):
    db.create_exp("test_exp", "test_project", None, None)
    db.update_exp(1, name="new_name", status=ExperimentStatus.RUNNING)
    exp = db.get_exp(1)
    assert exp.name == "new_name"
    assert exp.status == ExperimentStatus.RUNNING


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
