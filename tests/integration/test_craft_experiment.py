import asyncio

import pytest

import alphatrion as alpha
from alphatrion.runtime.runtime import global_runtime


@pytest.mark.asyncio
async def test_integration_craft_experiment():
    trial_id = None

    async def fake_work(duration: int):
        await asyncio.sleep(duration)
        print("duration done:", duration)

    async with alpha.CraftExperiment.setup(
        name="integration_test_exp",
        description="Integration test for CraftExperiment",
        meta={"test_case": "integration_craft_experiment"},
    ) as exp:
        async with exp.start_trial(
            name="integration_test_trial",
            description="Trial for integration test",
            meta={"trial_case": "integration_craft_trial"},
            config=alpha.TrialConfig(max_runs_per_trial=2),
        ) as trial:
            trial_id = trial.id

            trial.start_run(lambda: fake_work(1))
            trial.start_run(lambda: fake_work(2))
            trial.start_run(lambda: fake_work(4))
            trial.start_run(lambda: fake_work(5))
            trial.start_run(lambda: fake_work(6))

            await trial.wait()

    runtime = global_runtime()

    # Give some time for the runs to complete the done() callback.
    # Or the result below will always be right.
    await asyncio.sleep(1)

    runs = runtime.metadb.list_runs_by_trial_id(trial_id=trial_id)
    assert len(runs) == 5
    completed_runs = [run for run in runs if run.status == alpha.Status.COMPLETED]
    assert len(completed_runs) == 2
    cancelled_runs = [run for run in runs if run.status == alpha.Status.CANCELLED]
    assert len(cancelled_runs) == 3
