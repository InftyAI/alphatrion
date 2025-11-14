import asyncio
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta

import pytest

import alphatrion as alpha
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.trial.trial import current_trial_id


@pytest.mark.asyncio
async def test_log_artifact():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with alpha.CraftExperiment.setup(
        name="log_artifact_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(name="first-trial")

        exp_obj = exp._runtime._metadb.get_exp(exp_id=exp._id)
        assert exp_obj is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            await alpha.log_artifact(paths="file1.txt", version="v1")
            versions = exp._runtime._artifact.list_versions(exp_obj.uuid)
            assert "v1" in versions

            with open("file1.txt", "w") as f:
                f.write("This is modified file1.")

            # push folder instead
            await alpha.log_artifact(paths=["file1.txt"], version="v2")
            versions = exp._runtime._artifact.list_versions(exp_obj.uuid)
            assert "v2" in versions

        exp._runtime._artifact.delete(
            repo_name=exp_obj.uuid,
            versions=["v1", "v2"],
        )
        versions = exp._runtime._artifact.list_versions(exp_obj.uuid)
        assert len(versions) == 0

        trial.cancel()

        got_exp = exp._runtime._metadb.get_exp(exp_id=exp._id)
        assert got_exp is not None
        assert got_exp.name == "log_artifact_exp"

        got_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert got_trial is not None
        assert got_trial.name == "first-trial"
        assert got_trial.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_log_params():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with alpha.CraftExperiment.setup(name="log_params_exp") as exp:
        trial = exp.start_trial(name="first-trial", params={"param1": 0.1})

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial.id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.1}

        params = {"param1": 0.2}
        await alpha.log_params(params=params)

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial.id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.2}
        assert new_trial.status == TrialStatus.RUNNING
        assert current_trial_id.get() == trial.id

        trial.cancel()

        trial = exp.start_trial(name="second-trial", params={"param1": 0.1})
        assert current_trial_id.get() == trial.id
        trial.cancel()


@pytest.mark.asyncio
async def test_log_metrics():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def log_metric(metrics: dict):
        await alpha.log_metrics(metrics)

    async with alpha.CraftExperiment.setup(name="log_metrics_exp") as exp:
        trial = exp.start_trial(name="first-trial", params={"param1": 0.1})

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.1}

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 0

        run = trial.start_run(lambda: log_metric({"accuracy": 0.95, "loss": 0.1}))
        await run.wait()

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 2
        assert metrics[0].key == "accuracy"
        assert metrics[0].value == 0.95
        assert metrics[0].step == 1
        assert metrics[1].key == "loss"
        assert metrics[1].value == 0.1
        assert metrics[1].step == 1
        run_id_1 = metrics[0].run_id
        assert run_id_1 is not None
        assert metrics[0].run_id == metrics[1].run_id

        run = trial.start_run(lambda: log_metric({"accuracy": 0.96}))
        await run.wait()

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 3
        assert metrics[2].key == "accuracy"
        assert metrics[2].value == 0.96
        assert metrics[2].step == 2
        run_id_2 = metrics[2].run_id
        assert run_id_2 is not None
        assert run_id_2 != run_id_1

        trial.cancel()


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_max():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with alpha.CraftExperiment.setup(
        name="log_metrics_with_save_on_max",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            trial = exp.start_trial(
                name="trial-with-save_on_best",
                config=alpha.TrialConfig(
                    checkpoint=alpha.CheckpointConfig(
                        enabled=True,
                        path=tmpdir,
                        save_on_best=True,
                    ),
                    monitor_metric="accuracy",
                    monitor_mode="max",
                ),
            )

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            run = trial.start_run(lambda: log_metric(0.90))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = trial.start_run(lambda: log_metric(0.78))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            time.sleep(1)

            run = trial.start_run(lambda: log_metric(0.91))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 2

            time.sleep(1)

            run = trial.start_run(lambda: log_metric(0.98))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 3

            trial.cancel()


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_min():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with alpha.CraftExperiment.setup(
        name="log_metrics_with_save_on_min",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            trial = exp.start_trial(
                name="trial-with-save_on_best",
                config=alpha.TrialConfig(
                    checkpoint=alpha.CheckpointConfig(
                        enabled=True,
                        path=tmpdir,
                        save_on_best=True,
                    ),
                    monitor_metric="accuracy",
                    monitor_mode="min",
                ),
            )

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            run = trial.start_run(lambda: log_metric(0.30))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = trial.start_run(lambda: log_metric(0.58))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            time.sleep(1)

            run = trial.start_run(lambda: log_metric(0.21))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 2

            time.sleep(1)

            task = trial.start_run(lambda: log_metric(0.18))
            await task.wait()
            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 3

            trial.cancel()


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(100)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.CraftExperiment.setup(
        name="log_metrics_with_early_stopping"
    ) as exp:
        async with exp.start_trial(
            name="trial-with-early-stopping",
            config=alpha.TrialConfig(
                monitor_metric="accuracy",
                early_stopping_runs=2,
            ),
        ) as trial:
            trial.start_run(lambda: fake_work(0.5))
            trial.start_run(lambda: fake_work(0.6))
            trial.start_run(lambda: fake_work(0.2))
            trial.start_run(lambda: fake_work(0.7))
            trial.start_run(lambda: fake_sleep(0.2))
            # The first run that is worse than 0.6
            trial.start_run(lambda: fake_work(0.4))
            # The second run that is worse than 0.6, should trigger early stopping
            trial.start_run(lambda: fake_work(0.1))
            trial.start_run(lambda: fake_work(0.2))
            # trigger early stopping
            await trial.wait()

            assert len(trial._runtime._metadb.list_metrics(trial_id=trial.id)) == 6


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping_never_triggered():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(value)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.CraftExperiment.setup(
        name="log_metrics_with_both_early_stopping_and_timeout"
    ) as exp:
        async with exp.start_trial(
            name="trial-with-early-stopping",
            config=alpha.TrialConfig(
                monitor_metric="accuracy",
                early_stopping_runs=3,
                max_runtime_seconds=3,
            ),
        ) as trial:
            start_time = datetime.now()
            trial.start_run(lambda: fake_work(1))
            trial.start_run(lambda: fake_work(2))
            trial.start_run(lambda: fake_sleep(2))
            # running in parallel.
            await trial.wait()

            assert len(trial._runtime._metadb.list_metrics(trial_id=trial.id)) == 3
            assert datetime.now() - start_time >= timedelta(seconds=3)


@pytest.mark.asyncio
async def test_log_metrics_with_max_run_number():
    alpha.init(project_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with alpha.CraftExperiment.setup(
        name="log_metrics_with_max_run_number"
    ) as exp:
        async with exp.start_trial(
            name="trial-with-max-run-number",
            config=alpha.TrialConfig(
                monitor_metric="accuracy",
                max_runs_per_trial=5,
            ),
        ) as trial:
            while not trial.cancelled():
                run = trial.start_run(lambda: fake_work(1))
                await run.wait()

            assert len(trial._runtime._metadb.list_metrics(trial_id=trial.id)) == 5
