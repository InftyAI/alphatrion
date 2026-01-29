import asyncio

import pytest

import alphatrion as alpha
from alphatrion.experiment.craft_experiment import CraftExperiment
from alphatrion.runtime.runtime import global_runtime


@pytest.mark.asyncio
async def test_integration_project():
    exp_id = None

    async def fake_work(duration: int):
        await asyncio.sleep(duration)
        print("duration done:", duration)

    async with alpha.Project.setup(
        name="integration_test_project",
        description="Integration test for Project",
        meta={"test_case": "integration_project"},
    ):
        async with CraftExperiment.start(
            name="integration_test_experiment",
            description="Experiment for integration test",
            meta={"experiment_case": "integration_project_experiment"},
            config=alpha.ExperimentConfig(max_runs_per_experiment=2),
        ) as exp:
            exp_id = exp.id

            exp.start_run(lambda: fake_work(1))
            exp.start_run(lambda: fake_work(2))
            exp.start_run(lambda: fake_work(4))
            exp.start_run(lambda: fake_work(5))
            exp.start_run(lambda: fake_work(6))

            await exp.wait()

    runtime = global_runtime()

    # Give some time for the runs to complete the done() callback.
    # Or the result below will always be right.
    await asyncio.sleep(1)

    runs = runtime.metadb.list_runs_by_exp_id(exp_id=exp_id)
    assert len(runs) == 5
    completed_runs = [run for run in runs if run.status == alpha.Status.COMPLETED]
    assert len(completed_runs) == 2
    cancelled_runs = [run for run in runs if run.status == alpha.Status.CANCELLED]
    assert len(cancelled_runs) == 3
