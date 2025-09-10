import pytest

from alphatrion.model.model import Model
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def model():
    runtime = Runtime(project_id="test_project")
    model = Model(runtime=runtime)
    yield model


def test_model(model):
    model.create("test_model", "A test model", {"foo": "bar"}, {"env": "test"})
    model1 = model.get(1)
    assert model1 is not None
    assert model1.name == "test_model"
    assert model1.description == "A test model"
    assert model1.meta == {"foo": "bar"}

    model.update(1, labels={"env": "prod"})
    model1 = model.get(1)
    assert model1.labels == {"env": "prod"}

    models = model.list()
    assert len(models) == 1

    model.delete(1)
    model1 = model.get(1)
    assert model1 is None
