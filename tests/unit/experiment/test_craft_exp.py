import pytest

from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.runtime.runtime import init
from alphatrion.trial.trial import TrialConfig


@pytest.mark.asyncio
async def test_craft_experiment():
    init(project_id="test_project", artifact_insecure=True)

    async with CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        exp1 = exp._get()
        assert exp1 is not None
        assert exp1.name == "context_exp"
        assert exp1.description == "Context manager test"

        trial = await exp.start_trial(description="First trial")
        trial1 = trial._get()
        assert trial1 is not None
        assert trial1.description == "First trial"

        trial.stop()

        trial2 = trial._get()
        assert trial2.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_craft_experiment_with_context():
    init(project_id="test_project", artifact_insecure=True)

    async with CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = await exp.start_trial(
            description="First trial", config=TrialConfig(max_duration_seconds=2)
        )
        await trial.wait_stopped()
        assert trial.stopped()

        trial = trial._get()
        assert trial.status == TrialStatus.FINISHED
