from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.runtime.runtime import init


def test_craft_experiment():
    init(project_id="test_project", artifact_insecure=True)

    with CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        exp1 = exp._get()
        assert exp1 is not None
        assert exp1.name == "context_exp"
        assert exp1.description == "Context manager test"

        trial = exp.start_trial(description="First trial")
        trial1 = trial._get()
        assert trial1 is not None
        assert trial1.description == "First trial"

        trial.finish()

        trial2 = trial._get()
        assert trial2.status == TrialStatus.FINISHED
