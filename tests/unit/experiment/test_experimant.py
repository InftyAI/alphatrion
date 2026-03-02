# ruff: noqa: E501

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import faker
import pytest

from alphatrion.experiment import base as experiment
from alphatrion.experiment.base import (
    CheckpointConfig,
    ExperimentConfig,
)
from alphatrion.experiment.craft_experiment import CraftExperiment
from alphatrion.runtime.contextvars import current_exp_id
from alphatrion.runtime.runtime import global_runtime, init
from alphatrion.snapshot.snapshot import checkpoint_path
from alphatrion.storage.sql_models import Status


class TestExperimentConfig(unittest.IsolatedAsyncioTestCase):
    def test_config(self):
        test_cases = [
            {
                "name": "Default config",
                "config": {
                    "checkpoint.save_on_best": False,
                    "early_stopping_runs": -1,
                },
                "error": False,
            },
            {
                "name": "save_on_best True config",
                "config": {
                    "monitor_metric": "accuracy",
                    "checkpoint.save_on_best": True,
                    "early_stopping_runs": 2,
                },
                "error": False,
            },
            {
                "name": "Invalid config missing monitor_metric",
                "config": {
                    "checkpoint.save_on_best": True,
                    "early_stopping_runs": -1,
                },
                "error": True,
            },
            {
                "name": "Invalid config early_stopping_runs > 0",
                "config": {
                    "checkpoint.save_on_best": False,
                    "early_stopping_runs": 2,
                },
                "error": True,
            },
        ]

        init(team_id=uuid.uuid4(), user_id=uuid.uuid4())

        for case in test_cases:
            with self.subTest(name=case["name"]):
                if case["error"]:
                    with self.assertRaises(ValueError):
                        CraftExperiment(
                            config=ExperimentConfig(
                                monitor_metric=case["config"].get(
                                    "monitor_metric", None
                                ),
                                checkpoint=CheckpointConfig(
                                    save_on_best=case["config"].get(
                                        "checkpoint.save_on_best", False
                                    ),
                                ),
                                early_stopping_runs=case["config"].get(
                                    "early_stopping_runs", -1
                                ),
                            ),
                        )
                else:
                    _ = CraftExperiment(
                        config=ExperimentConfig(
                            monitor_metric=case["config"].get("monitor_metric", None),
                            checkpoint=CheckpointConfig(
                                save_on_best=case["config"].get(
                                    "checkpoint.save_on_best", False
                                ),
                            ),
                            early_stopping_runs=case["config"].get(
                                "early_stopping_runs", -1
                            ),
                        ),
                    )


@pytest.mark.asyncio
async def test_snapshot_path():
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    init(team_id=team_id, user_id=user_id)

    async with CraftExperiment.start(name=faker.Faker().word()) as exp:
        assert checkpoint_path() == (
            Path(exp._runtime.root_path)
            / "snapshots"
            / f"team_{team_id}"
            / f"user_{user_id}"
            / f"exp_{exp.id}"
            / "checkpoints"
        )


@pytest.mark.asyncio
async def test_experiment_with_done():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    exp_id = None
    async with CraftExperiment.start(name="first-experiment") as exp:
        exp_id = exp.id

    # exit the exp context, trial should be done automatically
    exp_obj = global_runtime().metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.duration is not None
    assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_experiment_with_done_with_err():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    exp_id = None
    run_id = None
    async with CraftExperiment.start(name="first-experiment") as exp:
        exp_id = exp.id

        run = exp.run(lambda: asyncio.sleep(2))
        run_id = run.id
        exp.done_with_err()

    # exit the proj context, trial should be done automatically
    exp_obj = global_runtime()._metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.duration is not None
    assert exp_obj.status == Status.FAILED

    assert global_runtime().metadb.get_run(run_id=run_id).status == Status.CANCELLED


@pytest.mark.asyncio
async def test_experiment_with_done_with_cancel():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    exp_id = None
    run_id = None
    async with CraftExperiment.start(name="first-experiment") as exp:
        exp_id = exp.id

        run = exp.run(lambda: asyncio.sleep(2))
        run_id = run.id
        exp.done_with_cancel()

    # exit the proj context, trial should be done automatically
    exp_obj = global_runtime().metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.duration is not None
    assert exp_obj.status == Status.CANCELLED

    assert global_runtime().metadb.get_run(run_id=run_id).status == Status.CANCELLED


@pytest.mark.asyncio
async def test_experiment_with_wait():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    async def fake_work():
        await asyncio.sleep(3)

    exp_id = None
    async with CraftExperiment.start(name="first-experiment") as exp:
        exp_id = current_exp_id.get()
        start_time = datetime.now()

        exp.run(fake_work)
        assert datetime.now() - start_time <= timedelta(seconds=1)

        await exp.wait()
        assert datetime.now() - start_time >= timedelta(seconds=3)

    exp_obj = exp._runtime.metadb.get_experiment(experiment_id=exp_id)
    assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_create_experiment_with_run():
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    init(
        team_id=team_id,
        user_id=user_id,
    )

    async def fake_work(exp_id: uuid.UUID):
        assert current_exp_id.get() == exp_id
        await asyncio.sleep(3)

    async with CraftExperiment.start(name="first-experiment") as exp:
        start_time = datetime.now()

        run1 = exp.run(lambda: fake_work(exp.id))
        assert len(exp._runs) == 1

        run2 = exp.run(lambda: fake_work(exp.id))
        assert len(exp._runs) == 2

        await exp.wait()
        assert datetime.now() - start_time >= timedelta(seconds=3)
        assert len(exp._runs) == 0

        run1_obj = run1._get_obj()
        assert run1_obj.status == Status.COMPLETED
        assert run1_obj.duration >= 3.0

        run2_obj = run2._get_obj()
        assert run2_obj.status == Status.COMPLETED
        assert run2_obj.duration >= 3.0


@pytest.mark.asyncio
async def test_create_experiment_with_run_cancelled():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    async def fake_work(timeout: int):
        await asyncio.sleep(timeout)

    async with CraftExperiment.start(
        name="first-experiment",
        config=experiment.ExperimentConfig(max_execution_seconds=2),
    ) as exp:
        run_0 = exp.run(lambda: fake_work(1))
        run_1 = exp.run(lambda: fake_work(4))
        run_2 = exp.run(lambda: fake_work(5))
        run_3 = exp.run(lambda: fake_work(6))
        # At this point, 4 runs are started.
        assert len(exp._runs) == 4
        await exp.wait()
        assert len(exp._runs) == 0

        run_0_obj = run_0._get_obj()
        assert run_0_obj.status == Status.COMPLETED
        assert run_0_obj.duration >= 1.0
        run_1_obj = run_1._get_obj()
        assert run_1_obj.status == Status.CANCELLED
        assert run_1_obj.duration >= 2.0
        run_2_obj = run_2._get_obj()
        assert run_2_obj.status == Status.CANCELLED
        assert run_2_obj.duration >= 2.0
        run_3_obj = run_3._get_obj()
        assert run_3_obj.status == Status.CANCELLED
        assert run_3_obj.duration >= 2.0


@pytest.mark.asyncio
async def test_create_experiment_with_max_execution_seconds():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    async with CraftExperiment.start(
        name="first-experiment",
        config=experiment.ExperimentConfig(max_execution_seconds=2),
    ) as exp:
        await exp.wait()
        assert exp.is_done()

        exp_obj = exp._get_obj()
        assert exp_obj.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_experiment_with_signal():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    async def fake_work(exp: CraftExperiment):
        await asyncio.sleep(2)
        exp._on_signal()

    start_time = datetime.now()
    async with CraftExperiment.start(
        name="first-experiment",
    ) as exp:
        exp.run(lambda: asyncio.sleep(5))
        exp.run(partial(fake_work, exp))
        await exp.wait()

    exp_obj = exp._get_obj()
    assert exp_obj.status == Status.CANCELLED
    assert (datetime.now() - start_time).total_seconds() >= 2
    assert (datetime.now() - start_time).total_seconds() < 5


@pytest.mark.asyncio
async def test_experiment_with_result_return():
    init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    async def fake_work():
        return {"foo": "bar"}

    async with CraftExperiment.start(
        name="first-experiment",
    ) as exp:
        run = exp.run(fake_work)
        await run.wait()
        assert run.result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_experiment_with_labels():
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    init(
        team_id=team_id,
        user_id=user_id,
    )

    async with CraftExperiment.start(
        name="first-experiment",
        labels="foo:bar,baz=qux",
    ) as exp:
        exp_obj = exp._get_obj()
        assert exp_obj is not None

        exp_labels = exp._runtime.metadb.list_exps_by_label(
            team_id=team_id,
            label_name="foo",
            label_value="bar",
        )

        assert len(exp_labels) == 1
