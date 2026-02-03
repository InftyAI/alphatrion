import asyncio

import pytest

from alphatrion import experiment, project
from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage.sql_models import Status


@pytest.mark.asyncio
async def test_integration_project():
    exp_id = None

    async def fake_work(duration: int):
        await asyncio.sleep(duration)
        print("duration done:", duration)

    async with project.Project.setup(
        name="integration_test_project",
        description="Integration test for Project",
        meta={"test_case": "integration_project"},
    ):
        async with experiment.CraftExperiment.start(
            name="integration_test_experiment",
            description="Experiment for integration test",
            meta={"experiment_case": "integration_project_experiment"},
            config=experiment.ExperimentConfig(max_runs_per_experiment=2),
        ) as exp:
            exp_id = exp.id

            exp.run(lambda: fake_work(1))
            exp.run(lambda: fake_work(2))
            exp.run(lambda: fake_work(4))
            exp.run(lambda: fake_work(5))
            exp.run(lambda: fake_work(6))

            await exp.wait()

    runtime = global_runtime()

    # Give some time for the runs to complete the done() callback.
    # Or the result below will always be right.
    await asyncio.sleep(1)

    runs = runtime.metadb.list_runs_by_exp_id(exp_id=exp_id)
    assert len(runs) == 5
    completed_runs = [run for run in runs if run.status == Status.COMPLETED]
    assert len(completed_runs) == 2
    cancelled_runs = [run for run in runs if run.status == Status.CANCELLED]
    assert len(cancelled_runs) == 3
