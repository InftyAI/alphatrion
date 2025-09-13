import time

from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import ExperimentStatus


def test_craft_experiment():
    with CraftExperiment.run(
        project_id="test_project",
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
        labels={"type": "unit"},
    ) as exp:
        time.sleep(1)
        assert exp.running_time() == 1

        exp1 = exp.get(1)
        assert exp1 is not None
        assert exp1.name == "context_exp"
        assert exp1.description == "Context manager test"
        assert exp1.status == ExperimentStatus.RUNNING

    assert exp.running_time() == 0

    exp1 = exp.get(1)
    assert exp1.status == ExperimentStatus.FINISHED
    assert exp1.duration > 0

    assert exp._steps == 0
    assert exp._start_at is None
    assert exp._best_metric_value is None
