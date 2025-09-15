from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import ExperimentStatus
from alphatrion.runtime.runtime import init


def test_craft_experiment():
    init(project_id="test_project", artifact_insecure=True)

    id = None

    with CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        id = exp._runtime._current_exp_id
        exp1 = exp.get(id)
        assert exp1 is not None
        assert exp1.name == "context_exp"
        assert exp1.description == "Context manager test"
        assert exp1.status == ExperimentStatus.RUNNING

    exp1 = exp.get(id)
    assert exp1.status == ExperimentStatus.FINISHED
    assert exp1.duration > 0

    assert exp._steps == 0
    assert exp._best_metric_value is None
