import pytest

from alphatrion.experiment.craft_exp import Experiment
from alphatrion.metadata.sql_models import ExperimentStatus
from alphatrion.runtime.runtime import init


@pytest.fixture
def exp():
    init(project_id="test_project", artifact_insecure=True)
    exp = Experiment()
    yield exp


def test_experiment_crud(exp):
    id = exp.create("test_exp", "A test experiment")
    exp1 = exp.get(id)
    assert exp1 is not None
    assert exp1.name == "test_exp"
    assert exp1.description == "A test experiment"
    assert exp1.status == ExperimentStatus.PENDING
    assert exp1.duration == 0
    assert len(exp.list_paginated()) == 1

    exp.update_tags(id, {"env": "prod"})
    exp1 = exp.get(id)
    assert exp1.meta["tags"] == {"env": "prod"}


def test_experiment_start(exp):
    id = exp._start()
    exp1 = exp.get(id)
    assert exp1.status == ExperimentStatus.RUNNING

    # reset current exp id to simulate a new session
    exp._runtime._current_exp_id = id

    exp._stop(id)
    exp1 = exp.get(id)
    assert exp1.status == ExperimentStatus.FINISHED
    assert exp1.duration > 0
