import asyncio
import random
import uuid
from datetime import datetime, timedelta

import pytest

from alphatrion.experiment import base as experiment
from alphatrion.metadata.sql_models import Status
from alphatrion.project.project import Project, ProjectConfig
from alphatrion.runtime.runtime import global_runtime, init


@pytest.mark.asyncio
async def test_project():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        proj1 = proj._get()
        assert proj1 is not None
        assert proj1.name == "context_proj"
        assert proj1.description == "Context manager test"

        exp = proj.start_experiment(name="first-experiment")
        exp_obj = exp._get_obj()
        assert exp_obj is not None
        assert exp_obj.name == "first-experiment"

        exp.done()

        exp_obj = exp._get_obj()
        assert exp_obj.duration is not None
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_project_with_done():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    exp_id = None
    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        exp = proj.start_experiment(name="first-experiment")
        exp_id = exp.id

    # exit the exp context, trial should be done automatically
    exp_obj = global_runtime()._metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.duration is not None
    assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_project_with_done_with_err():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    exp_id = None
    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        exp = proj.start_experiment(name="first-experiment")
        exp_id = exp.id
        exp.done_with_err()

    # exit the proj context, trial should be done automatically
    exp_obj = global_runtime()._metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.duration is not None
    assert exp_obj.status == Status.FAILED


@pytest.mark.asyncio
async def test_project_with_no_context():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(exp: experiment.Experiment):
        await asyncio.sleep(3)
        exp.done()

    proj = Project.setup(name="no_context_proj")
    async with proj.start_experiment(name="first-trial") as exp:
        exp.start_run(lambda: fake_work(exp))
        await exp.wait()

        exp_obj = exp._get_obj()
        assert exp_obj.duration is not None
        assert exp_obj.status == Status.COMPLETED

    proj.done()


@pytest.mark.asyncio
async def test_project_with_exp():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    exp_id = None
    async with Project.setup(name="context_proj") as proj:
        async with proj.start_experiment(name="first-exp") as exp:
            exp_obj = exp._get_obj()
            assert exp_obj is not None
            assert exp_obj.name == "first-exp"
            exp_id = experiment.current_exp_id.get()

        exp_obj = proj._runtime._metadb.get_experiment(experiment_id=exp_id)
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_project_with_exp_wait():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(exp: experiment.Experiment):
        await asyncio.sleep(3)
        exp.done()

    exp_id = None
    async with Project.setup(name="context_proj") as proj:
        async with proj.start_experiment(name="first-experiment") as exp:
            exp_id = experiment.current_exp_id.get()
            start_time = datetime.now()

            asyncio.create_task(fake_work(exp))
            assert datetime.now() - start_time <= timedelta(seconds=1)

            await exp.wait()
            assert datetime.now() - start_time >= timedelta(seconds=3)

        exp_obj = exp._runtime._metadb.get_experiment(experiment_id=exp_id)
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_project_with_run():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(cancel_func: callable, exp_id: uuid.UUID):
        assert experiment.current_exp_id.get() == exp_id
        await asyncio.sleep(3)
        cancel_func()

    async with (
        Project.setup(name="context_proj") as proj,
        proj.start_experiment(name="first-experiment") as exp,
    ):
        start_time = datetime.now()

        exp.start_run(lambda: fake_work(exp.done, exp.id))
        assert len(exp._runs) == 1

        exp.start_run(lambda: fake_work(exp.done, exp.id))
        assert len(exp._runs) == 2

        await exp.wait()
        assert datetime.now() - start_time >= timedelta(seconds=3)
        assert len(exp._runs) == 0


@pytest.mark.asyncio
async def test_create_project_with_run_cancelled():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(timeout: int):
        await asyncio.sleep(timeout)

    async with (
        Project.setup(name="context_proj") as proj,
        proj.start_experiment(
            name="first-experiment",
            config=experiment.ExperimentConfig(max_execution_seconds=2),
        ) as exp,
    ):
        run_0 = exp.start_run(lambda: fake_work(1))
        run_1 = exp.start_run(lambda: fake_work(4))
        run_2 = exp.start_run(lambda: fake_work(5))
        run_3 = exp.start_run(lambda: fake_work(6))
        # At this point, 4 runs are started.
        assert len(exp._runs) == 4
        await exp.wait()

        run_0_obj = run_0._get_obj()
        assert run_0_obj.status == Status.COMPLETED
        run_1_obj = run_1._get_obj()
        assert run_1_obj.status == Status.CANCELLED
        run_2_obj = run_2._get_obj()
        assert run_2_obj.status == Status.CANCELLED
        run_3_obj = run_3._get_obj()
        assert run_3_obj.status == Status.CANCELLED


@pytest.mark.asyncio
async def test_create_project_with_max_execution_seconds():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        exp = proj.start_experiment(
            name="first-experiment",
            config=experiment.ExperimentConfig(max_execution_seconds=2),
        )
        await exp.wait()
        assert exp.is_done()

        exp = exp._get_obj()
        assert exp.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_project_with_multi_trials_in_parallel():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work():
        proj = global_runtime().current_proj

        duration = random.randint(1, 5)
        exp = proj.start_experiment(
            name="first-experiment",
            config=experiment.ExperimentConfig(max_execution_seconds=duration),
        )
        # double check current trial id.
        assert exp.id == experiment.current_exp_id.get()

        await exp.wait()
        assert exp.is_done()
        # we don't reset the current trial id.
        assert exp.id == experiment.current_exp_id.get()

        exp = exp._get_obj()
        assert exp.status == Status.COMPLETED

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
    ):
        await asyncio.gather(
            fake_work(),
            fake_work(),
            fake_work(),
        )
        print("All trials finished.")


@pytest.mark.asyncio
async def test_project_with_config():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
        config=ProjectConfig(max_execution_seconds=2),
    ) as proj:
        exp = proj.start_experiment(name="first-experiment")
        await exp.wait()
        assert exp.is_done()

        exp_obj = exp._get_obj()
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_project_with_hierarchy_timeout():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
        config=ProjectConfig(max_execution_seconds=2),
    ) as proj:
        start_time = datetime.now()
        exp = proj.start_experiment(
            name="first-experiment",
            config=experiment.ExperimentConfig(max_execution_seconds=5),
        )
        await exp.wait()
        assert exp.is_done()

        assert (datetime.now() - start_time).total_seconds() >= 2
        assert (datetime.now() - start_time).total_seconds() < 5

        exp_obj = exp._get_obj()
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_project_with_hierarchy_timeout_2():
    init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    start_time = datetime.now()

    async with Project.setup(
        name="context_proj",
        description="Context manager test",
        meta={"key": "value"},
        config=ProjectConfig(max_execution_seconds=5),
    ) as proj:
        exp = proj.start_experiment(
            name="first-experiment",
            config=experiment.ExperimentConfig(max_execution_seconds=2),
        )
        await exp.wait()
        assert exp.is_done()

        assert (datetime.now() - start_time).total_seconds() >= 2

        exp_obj = exp._get_obj()
        assert exp_obj.status == Status.COMPLETED

    assert (datetime.now() - start_time).total_seconds() < 5
