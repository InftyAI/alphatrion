import asyncio
import random
import uuid
from datetime import datetime, timedelta

import pytest

from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.runtime.runtime import init
from alphatrion.trial.trial import Trial, TrialConfig, current_trial_id


@pytest.mark.asyncio
async def test_craft_experiment():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with CraftExperiment.start(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        exp1 = exp._get()
        assert exp1 is not None
        assert exp1.name == "context_exp"
        assert exp1.description == "Context manager test"

        trial = exp.start_trial(name="first-trial")
        trial_obj = trial._get_obj()
        assert trial_obj is not None
        assert trial_obj.name == "first-trial"

        trial.cancel()

        trial2 = trial._get_obj()
        assert trial2.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_create_experiment_with_trial():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    trial_id = None
    async with CraftExperiment.start(name="context_exp") as exp:
        async with exp.start_trial(name="first-trial") as trial:
            trial_obj = trial._get_obj()
            assert trial_obj is not None
            assert trial_obj.name == "first-trial"
            trial_id = current_trial_id.get()

        trial_obj = exp._runtime._metadb.get_trial(trial_id=trial_id)
        assert trial_obj.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_create_experiment_with_trial_wait():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(trial: Trial):
        await asyncio.sleep(3)
        trial.cancel()

    trial_id = None
    async with CraftExperiment.start(name="context_exp") as exp:
        async with exp.start_trial(name="first-trial") as trial:
            trial_id = current_trial_id.get()
            start_time = datetime.now()

            asyncio.create_task(fake_work(trial))
            assert datetime.now() - start_time <= timedelta(seconds=1)

            await trial.wait()
            assert datetime.now() - start_time >= timedelta(seconds=3)

        trial_obj = exp._runtime._metadb.get_trial(trial_id=trial_id)
        assert trial_obj.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_create_experiment_with_run():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(cancel_func: callable):
        await asyncio.sleep(3)
        cancel_func()

    async with (
        CraftExperiment.start(name="context_exp") as exp,
        exp.start_trial(name="first-trial") as trial,
    ):
        start_time = datetime.now()

        trial.start_run(lambda: fake_work(trial.cancel))
        assert len(trial._running_tasks) == 1
        assert len(trial._runs) == 1

        trial.start_run(lambda: fake_work(trial.cancel))
        assert len(trial._running_tasks) == 2
        assert len(trial._runs) == 2

        await trial.wait()
        assert datetime.now() - start_time >= timedelta(seconds=3)
        assert len(trial._running_tasks) == 0
        assert len(trial._runs) == 0


@pytest.mark.asyncio
async def test_craft_experiment_with_context():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with CraftExperiment.start(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(
            name="first-trial", config=TrialConfig(max_duration_seconds=2)
        )
        await trial.wait()
        assert trial.stopped()

        trial = trial._get_obj()
        assert trial.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_craft_experiment_with_multi_trials_in_parallel():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(exp: CraftExperiment):
        duration = random.randint(1, 5)
        trial = exp.start_trial(
            name="first-trial", config=TrialConfig(max_duration_seconds=duration)
        )
        # double check current trial id.
        assert trial.id == current_trial_id.get()

        await trial.wait()
        assert trial.stopped()
        # we don't reset the current trial id.
        assert trial.id == current_trial_id.get()

        trial = trial._get_obj()
        assert trial.status == TrialStatus.FINISHED

    async with CraftExperiment.start(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        await asyncio.gather(
            fake_work(exp),
            fake_work(exp),
            fake_work(exp),
        )
        print("All trials finished.")
