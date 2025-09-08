import os
import pytest
from alphatrion import consts
from alphatrion.experiment.base import Experiment
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def exp():
    os.environ[consts.METADATA_DB_URL] = "sqlite:///:memory:"
    runtime = Runtime(project_id="test_project")
    exp = Experiment(runtime=runtime)
    yield exp

def test_abstract_methods(exp):
    with pytest.raises(NotImplementedError):
        exp.create("test_exp")

    with pytest.raises(NotImplementedError):
        exp.delete(1)

    with pytest.raises(NotImplementedError):
        exp.get(1)

    with pytest.raises(NotImplementedError):
        exp.start(1)

    with pytest.raises(NotImplementedError):
        exp.stop(1)

    with pytest.raises(NotImplementedError):
        exp.status(1)
