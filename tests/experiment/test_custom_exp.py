import os

import pytest

from alphatrion.metadata.sql_models import ExperimentStatus
from alphatrion import consts
from alphatrion.experiment.custom_exp import CustomExperiment
from alphatrion.runtime.runtime import Runtime

@pytest.fixture
def exp():
    os.environ[consts.METADATA_DB_URL] = "sqlite:///:memory:"
    runtime = Runtime(project_id="test_project")
    exp = CustomExperiment(runtime=runtime)
    yield exp

def test_custom_experiment(exp):
    exp.create("test_exp", "A test experiment", {"foo": "bar"})
    exp1 = exp.get(1)
    assert exp1 is not None
    assert exp1.name == "test_exp"
    assert exp1.description == "A test experiment"
    assert exp1.meta == {"foo": "bar"}
    assert exp1.status == ExperimentStatus.PENDING

    exp.start(1)
    exp1 = exp.get(1)
    assert exp1.status == ExperimentStatus.RUNNING

    exp.stop(1, status=ExperimentStatus.FAILED)
    exp1 = exp.get(1)
    assert exp1.status == ExperimentStatus.FAILED

    exp.delete(1)
    exp1 = exp.get(1)
    assert exp1 is None
