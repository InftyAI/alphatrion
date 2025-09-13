import pytest

from alphatrion.experiment.craft_exp import Experiment
from alphatrion.metadata.sql_models import ExperimentStatus
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def exp():
    runtime = Runtime(project_id="test_project")
    exp = Experiment(runtime=runtime)
    yield exp


def test_experiment_crud(exp):
    exp.create("test_exp", "A test experiment", {"foo": "bar"}, {"env": "test"})
    exp1 = exp.get(1)
    assert exp1 is not None
    assert exp1.name == "test_exp"
    assert exp1.description == "A test experiment"
    assert exp1.meta == {"foo": "bar"}
    assert exp1.status == ExperimentStatus.PENDING
    assert exp1.duration == 0
    assert len(exp.list_paginated()) == 1

    exp.update_labels(1, {"env": "prod"})
    exp1 = exp.get(1)
    assert exp1.labels == {"env": "prod"}


def test_experiment_start(exp):
    exp.start()
    exp1 = exp.get(1)
    assert exp1.status == ExperimentStatus.RUNNING

    exp.stop(1, status=ExperimentStatus.FAILED)
    exp1 = exp.get(1)
    assert exp1.status == ExperimentStatus.FAILED
    assert exp1.duration > 0
