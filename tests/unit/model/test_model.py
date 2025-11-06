import uuid

import pytest

from alphatrion.model.model import Model
from alphatrion.runtime.runtime import Runtime


@pytest.fixture
def model():
    runtime = Runtime(project_id="test_project", init_tables=True)
    model = Model(runtime=runtime)
    yield model


def test_model(model):
    project_id = uuid.uuid4()
    id = model.create(
        "test_model", project_id, "A test model", {"tags": {"foo": "bar"}}
    )
    model1 = model.get(id)
    assert model1 is not None
    assert model1.name == "test_model"
    assert model1.description == "A test model"
    assert model1.meta == {"tags": {"foo": "bar"}}

    model.update(id, meta={"tags": {"foo": "fuz"}})
    model1 = model.get(id)
    assert model1.meta == {"tags": {"foo": "fuz"}}

    models = model.list()
    assert len(models) == 1

    model.delete(id)
    model1 = model.get(id)
    assert model1 is None
