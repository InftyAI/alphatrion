import asyncio
import random
import uuid
from datetime import datetime, timedelta

import pytest

from alphatrion.experiment.craft_exp import CraftExperiment
from alphatrion.metadata.sql_models import Status
from alphatrion.runtime.runtime import global_runtime, init
from alphatrion.trial.trial import Trial, TrialConfig, current_trial_id


@pytest.mark.asyncio
async def test_craft_experiment():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with CraftExperiment.setup(
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

        trial.done()

        trial_obj = trial._get_obj()
        assert trial_obj.duration is not None
        assert trial_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_craft_experiment_with_done():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    trial_id = None
    async with CraftExperiment.setup(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(name="first-trial")
        trial_id = trial.id

    # exit the exp context, trial should be done automatically
    trial_obj = global_runtime()._metadb.get_trial(trial_id=trial_id)
    assert trial_obj.duration is not None
    assert trial_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_craft_experiment_with_done_with_err():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    trial_id = None
    async with CraftExperiment.setup(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(name="first-trial")
        trial_id = trial.id
        trial.done_with_err()

    # exit the exp context, trial should be done automatically
    trial_obj = global_runtime()._metadb.get_trial(trial_id=trial_id)
    assert trial_obj.duration is not None
    assert trial_obj.status == Status.FAILED


@pytest.mark.asyncio
async def test_craft_experiment_with_no_context():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(trial: Trial):
        await asyncio.sleep(3)
        trial.done()

    exp = CraftExperiment.setup(name="no_context_exp")
    async with exp.start_trial(name="first-trial") as trial:
        trial.start_run(lambda: fake_work(trial))
        await trial.wait()

        trial_obj = trial._get_obj()
        assert trial_obj.duration is not None
        assert trial_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_experiment_with_trial():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    trial_id = None
    async with CraftExperiment.setup(name="context_exp") as exp:
        async with exp.start_trial(name="first-trial") as trial:
            trial_obj = trial._get_obj()
            assert trial_obj is not None
            assert trial_obj.name == "first-trial"
            trial_id = current_trial_id.get()

        trial_obj = exp._runtime._metadb.get_trial(trial_id=trial_id)
        assert trial_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_experiment_with_trial_wait():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(trial: Trial):
        await asyncio.sleep(3)
        trial.done()

    trial_id = None
    async with CraftExperiment.setup(name="context_exp") as exp:
        async with exp.start_trial(name="first-trial") as trial:
            trial_id = current_trial_id.get()
            start_time = datetime.now()

            asyncio.create_task(fake_work(trial))
            assert datetime.now() - start_time <= timedelta(seconds=1)

            await trial.wait()
            assert datetime.now() - start_time >= timedelta(seconds=3)

        trial_obj = exp._runtime._metadb.get_trial(trial_id=trial_id)
        assert trial_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_experiment_with_run():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(cancel_func: callable, trial_id: uuid.UUID):
        assert current_trial_id.get() == trial_id
        await asyncio.sleep(3)
        cancel_func()

    async with (
        CraftExperiment.setup(name="context_exp") as exp,
        exp.start_trial(name="first-trial") as trial,
    ):
        start_time = datetime.now()

        trial.start_run(lambda: fake_work(trial.done, trial.id))
        assert len(trial._runs) == 1

        trial.start_run(lambda: fake_work(trial.done, trial.id))
        assert len(trial._runs) == 2

        await trial.wait()
        assert datetime.now() - start_time >= timedelta(seconds=3)
        assert len(trial._runs) == 0


@pytest.mark.asyncio
async def test_create_experiment_with_run_cancelled():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(timeout: int):
        await asyncio.sleep(timeout)

    async with (
        CraftExperiment.setup(name="context_exp") as exp,
        exp.start_trial(
            name="first-trial", config=TrialConfig(max_execution_seconds=2)
        ) as trial,
    ):
        run_0 = trial.start_run(lambda: fake_work(1))
        run_1 = trial.start_run(lambda: fake_work(4))
        run_2 = trial.start_run(lambda: fake_work(5))
        run_3 = trial.start_run(lambda: fake_work(6))
        # At this point, 4 runs are started.
        assert len(trial._runs) == 4
        await trial.wait()

        run_0_obj = run_0._get_obj()
        assert run_0_obj.status == Status.COMPLETED
        run_1_obj = run_1._get_obj()
        assert run_1_obj.status == Status.CANCELLED
        run_2_obj = run_2._get_obj()
        assert run_2_obj.status == Status.CANCELLED
        run_3_obj = run_3._get_obj()
        assert run_3_obj.status == Status.CANCELLED


@pytest.mark.asyncio
async def test_craft_experiment_with_context():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with CraftExperiment.setup(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(
            name="first-trial", config=TrialConfig(max_execution_seconds=2)
        )
        await trial.wait()
        assert trial.is_done()

        trial = trial._get_obj()
        assert trial.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_craft_experiment_with_multi_trials_in_parallel():
    init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work():
        exp = global_runtime().current_exp

        duration = random.randint(1, 5)
        trial = exp.start_trial(
            name="first-trial", config=TrialConfig(max_execution_seconds=duration)
        )
        # double check current trial id.
        assert trial.id == current_trial_id.get()

        await trial.wait()
        assert trial.is_done()
        # we don't reset the current trial id.
        assert trial.id == current_trial_id.get()

        trial = trial._get_obj()
        assert trial.status == Status.COMPLETED

    async with CraftExperiment.setup(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ):
        await asyncio.gather(
            fake_work(),
            fake_work(),
            fake_work(),
        )
        print("All trials finished.")
