import asyncio
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta

import pytest

import alphatrion as alpha
from alphatrion import experiment
from alphatrion.log.log import BEST_RESULT_PATH
from alphatrion.runtime.contextvars import current_exp_id
from alphatrion.storage.sql_models import Status


@pytest.mark.asyncio
async def test_log_artifact():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async with experiment.CraftExperiment.start(name="first-exp") as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file = "file.txt"
            with open(file, "w") as f:
                f.write("This is file1.")

            address = await alpha.log_artifact(
                paths=file,
                repo_name="log_artifact_repo",
                version="v1",
            )
            print("Logged artifact address:", address)
            assert address == f"{exp._runtime._team_id}/log_artifact_repo:v1"
            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime._team_id}/log_artifact_repo"
            )
            assert "v1" in versions

            with open(file, "w") as f:
                f.write("This is modified file1.")

            # push folder instead
            address = await alpha.log_artifact(
                paths=[file],
                repo_name="log_artifact_repo",
                version="v2",
            )
            assert address == f"{exp._runtime._team_id}/log_artifact_repo:v2"
            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime._team_id}/log_artifact_repo"
            )
            assert "v2" in versions

            exp._runtime._artifact.delete(
                repo_name=f"{exp._runtime._team_id}/log_artifact_repo",
                versions=["v1", "v2"],
            )
            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime._team_id}/log_artifact_repo"
            )
            assert len(versions) == 0

            exp_id = exp.id

            got_exp = exp._runtime._metadb.get_experiment(experiment_id=exp_id)
            assert got_exp.status == Status.RUNNING

    got_exp = exp._runtime._metadb.get_experiment(experiment_id=exp_id)
    assert got_exp is not None
    assert got_exp.name == "first-exp"
    assert got_exp.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_log_params():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async with experiment.CraftExperiment.start(
        name="first-exp", params={"param1": 0.1}
    ) as exp:
        new_exp = exp._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.1}

        params = {"param1": 0.2}
        await alpha.log_params(params=params)

        new_exp = exp._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.2}
        assert new_exp.status == Status.RUNNING
        assert current_exp_id.get() == exp.id

    assert current_exp_id.get() is None

    async with experiment.CraftExperiment.start(
        name="second-exp", params={"param1": 0.1}
    ) as exp:
        assert current_exp_id.get() == exp.id
    assert current_exp_id.get() is None


@pytest.mark.asyncio
async def test_log_metrics():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def log_metric(metrics: dict):
        await alpha.log_metrics(metrics)

    async with experiment.CraftExperiment.start(
        name="first-exp", params={"param1": 0.1}
    ) as exp:
        new_exp = exp._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.1}

        metrics = exp._runtime._metadb.list_metrics_by_experiment_id(
            experiment_id=exp.id
        )
        assert len(metrics) == 0

        run = exp.run(lambda: log_metric({"accuracy": 0.95, "loss": 0.1}))
        await run.wait()

        metrics = exp._runtime._metadb.list_metrics_by_experiment_id(
            experiment_id=exp.id
        )
        assert len(metrics) == 2
        assert metrics[0].key == "accuracy"
        assert metrics[0].value == 0.95
        assert metrics[1].key == "loss"
        assert metrics[1].value == 0.1
        run_id_1 = metrics[0].run_id
        assert run_id_1 is not None
        assert metrics[0].run_id == metrics[1].run_id

        run = exp.run(lambda: log_metric({"accuracy": 0.96}))
        await run.wait()

        metrics = exp._runtime._metadb.list_metrics_by_experiment_id(
            experiment_id=exp.id
        )
        assert len(metrics) == 3
        assert metrics[2].key == "accuracy"
        assert metrics[2].value == 0.96
        run_id_2 = metrics[2].run_id
        assert run_id_2 is not None
        assert run_id_2 != run_id_1


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_max():
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    alpha.init(team_id=team_id, user_id=user_id, org_id=org_id)

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    def find_unused_version(used_versions, all_versions):
        for v in all_versions:
            if v not in used_versions:
                return v
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        file = "file.txt"

        def pre_save_hook():
            with open(file, "a") as f:
                f.write("This is pre_save_hook modified file.\n")

        async with experiment.CraftExperiment.start(
            name="exp-with-save_on_best",
            config=experiment.ExperimentConfig(
                checkpoint=experiment.CheckpointConfig(
                    enabled=True,
                    path=tmpdir,
                    save_on_best=True,
                    pre_save_hook=pre_save_hook,
                ),
                monitor_metric="accuracy",
                # Make sure raw max also works.
                monitor_mode="max",
            ),
        ) as exp:
            with open(file, "w") as f:
                f.write("This is file.\n")

            run = exp.run(lambda: log_metric(0.90))
            await run.wait()

            # We need this because the returned version is unordered.
            used_version = []

            versions = exp._runtime._artifact.list_versions(f"{team_id}/ckpt")
            assert len(versions) == 1
            run_obj = run._get_obj()
            fixed_version = versions[0]
            used_version.append(fixed_version)
            assert run_obj.meta[BEST_RESULT_PATH] == f"{team_id}/ckpt:" + fixed_version
            with open(file) as f:
                assert len(f.readlines()) == 2

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = exp.run(lambda: log_metric(0.78))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(f"{team_id}/ckpt")
            assert len(versions) == 1

            time.sleep(1)

            run = exp.run(lambda: log_metric(0.91))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(f"{team_id}/ckpt")
            assert len(versions) == 2

            fixed_version = find_unused_version(used_version, versions)
            used_version.append(fixed_version)
            run_obj = run._get_obj()
            assert run_obj.meta[BEST_RESULT_PATH] == f"{team_id}/ckpt:" + fixed_version

            with open(file) as f:
                assert len(f.readlines()) == 3

            time.sleep(1)

            run = exp.run(lambda: log_metric(0.98))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(f"{team_id}/ckpt")
            assert len(versions) == 3
            run_obj = run._get_obj()

            fixed_version = find_unused_version(used_version, versions)
            used_version.append(fixed_version)
            assert run_obj.meta[BEST_RESULT_PATH] == f"{team_id}/ckpt:" + fixed_version
            with open(file) as f:
                assert len(f.readlines()) == 4


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_min():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        async with experiment.CraftExperiment.start(
            name="exp-with-save_on_best",
            config=experiment.ExperimentConfig(
                checkpoint=experiment.CheckpointConfig(
                    enabled=True,
                    path=tmpdir,
                    save_on_best=True,
                ),
                monitor_metric="accuracy",
                monitor_mode=experiment.MonitorMode.MIN,
            ),
        ) as exp:
            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            run = exp.run(lambda: log_metric(0.30))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime.team_id}/ckpt"
            )
            assert len(versions) == 1

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = exp.run(lambda: log_metric(0.58))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime.team_id}/ckpt"
            )
            assert len(versions) == 1

            time.sleep(1)

            run = exp.run(lambda: log_metric(0.21))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime.team_id}/ckpt"
            )
            assert len(versions) == 2

            time.sleep(1)

            task = exp.run(lambda: log_metric(0.18))
            await task.wait()
            versions = exp._runtime._artifact.list_versions(
                f"{exp._runtime.team_id}/ckpt"
            )
            assert len(versions) == 3


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(100)
        await alpha.log_metrics({"accuracy": value})

    async with experiment.CraftExperiment.start(
        name="exp-with-early-stopping",
        config=experiment.ExperimentConfig(
            monitor_metric="accuracy",
            early_stopping_runs=2,
        ),
    ) as exp:
        exp.run(lambda: fake_work(0.5))
        exp.run(lambda: fake_work(0.6))
        exp.run(lambda: fake_work(0.2))
        exp.run(lambda: fake_work(0.7))
        exp.run(lambda: fake_sleep(0.2))
        # The first run that is worse than 0.6
        exp.run(lambda: fake_work(0.4))
        # The second run that is worse than 0.6, should trigger early stopping
        exp.run(lambda: fake_work(0.1))
        exp.run(lambda: fake_work(0.2))
        # trigger early stopping
        await exp.wait()

        assert (
            len(
                exp._runtime._metadb.list_metrics_by_experiment_id(experiment_id=exp.id)
            )
            == 6
        )


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping_never_triggered():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(value)
        await alpha.log_metrics({"accuracy": value})

    async with experiment.CraftExperiment.start(
        name="exp-with-early-stopping",
        config=experiment.ExperimentConfig(
            monitor_metric="accuracy",
            early_stopping_runs=2,
            max_execution_seconds=3,
        ),
    ) as exp:
        start_time = datetime.now()
        exp.run(lambda: fake_work(3))
        exp.run(lambda: fake_work(1))
        exp.run(lambda: fake_sleep(5))
        # running in parallel.
        await exp.wait()

        assert (
            len(exp._runtime.metadb.list_metrics_by_experiment_id(experiment_id=exp.id))
            == 2
        )
        assert datetime.now() - start_time >= timedelta(seconds=3)


@pytest.mark.asyncio
async def test_log_metrics_with_max_run_number():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with experiment.CraftExperiment.start(
        name="exp-with-max-run-number",
        config=experiment.ExperimentConfig(
            monitor_metric="accuracy",
            max_runs_per_experiment=5,
        ),
    ) as exp:
        while not exp.is_done():
            run = exp.run(lambda: fake_work(1))
            await run.wait()

        assert (
            len(
                exp._runtime._metadb.list_metrics_by_experiment_id(experiment_id=exp.id)
            )
            == 5
        )


@pytest.mark.asyncio
async def test_log_metrics_with_max_target_meet():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(10)
        await alpha.log_metrics({"accuracy": value})

    async with experiment.CraftExperiment.start(
        name="exp-with-max-target-meet",
        config=experiment.ExperimentConfig(
            monitor_metric="accuracy",
            target_metric_value=0.9,
        ),
    ) as exp:
        exp.run(lambda: fake_work(0.5))
        exp.run(lambda: fake_work(0.3))
        exp.run(lambda: fake_sleep(0.4))
        exp.run(lambda: fake_work(0.9))
        await exp.wait()

        assert (
            len(
                exp._runtime._metadb.list_metrics_by_experiment_id(experiment_id=exp.id)
            )
            == 3
        )


@pytest.mark.asyncio
async def test_log_metrics_with_min_target_meet():
    alpha.init(
        team_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(3)
        await alpha.log_metrics({"accuracy": value})

    async with experiment.CraftExperiment.start(
        name="exp-with-min-target-meet",
        config=experiment.ExperimentConfig(
            monitor_metric="accuracy",
            target_metric_value=0.2,
            monitor_mode=experiment.MonitorMode.MIN,
        ),
    ) as exp:
        exp.run(lambda: fake_work(0.5))
        exp.run(lambda: fake_work(0.3))
        exp.run(lambda: fake_sleep(0.4))
        exp.run(lambda: fake_work(0.2))
        await exp.wait()

        assert (
            len(
                exp._runtime._metadb.list_metrics_by_experiment_id(experiment_id=exp.id)
            )
            == 3
        )


@pytest.mark.asyncio
async def test_log_dataset_with_json():
    team_id = uuid.uuid4()
    alpha.init(
        team_id=team_id,
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_worker():
        await alpha.log_dataset(
            name="test_dataset.json",
            data_or_path={
                "example": "test",
                "value": 123,
                "flag": True,
                "list": [1, 2, 3],
                "dict": {"a": 1, "b": 2},
            },
        )

    async with experiment.CraftExperiment.start(
        name="exp-log-dataset",
    ) as exp:
        await alpha.log_params({"temp": 0.5, "lr": 0.01})

        run = exp.run(lambda: fake_worker())
        await run.wait()

        run_obj = run._get_obj()
        assert run_obj is not None
        runtime = exp._runtime

        list_versions = runtime._artifact.list_versions(f"{team_id}/dataset")
        assert len(list_versions) == 1
        datasets = runtime._metadb.list_datasets(team_id=team_id, run_id=run_obj.uuid)
        assert len(datasets) == 1
        assert datasets[0].name == "test_dataset.json"
        assert datasets[0].team_id == team_id
        assert datasets[0].user_id == runtime._user_id
        assert datasets[0].experiment_id == exp.id
        assert datasets[0].run_id == run_obj.uuid
        assert datasets[0].path == f"{runtime.team_id}/dataset:{list_versions[0]}"
        assert int(datasets[0].meta["size"]) > 0


@pytest.mark.asyncio
async def test_log_dataset_with_file():
    team_id = uuid.uuid4()
    alpha.init(
        team_id=team_id,
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
    )

    async def fake_worker():
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            file_path = "test_dataset.txt"
            with open(file_path, "w") as f:
                f.write("This is a test dataset file.")

            await alpha.log_dataset(
                name="test_dataset",
                data_or_path=file_path,
            )

    async with experiment.CraftExperiment.start(
        name="exp-log-dataset",
    ) as exp:
        await alpha.log_params({"temp": 0.5, "lr": 0.01})

        run = exp.run(lambda: fake_worker())
        await run.wait()

        run_obj = run._get_obj()
        assert run_obj is not None
        runtime = exp._runtime

        list_versions = runtime._artifact.list_versions(f"{runtime.team_id}/dataset")
        assert len(list_versions) == 1
        datasets = runtime._metadb.list_datasets(team_id=team_id, run_id=run_obj.uuid)
        assert len(datasets) == 1
        assert datasets[0].name == "test_dataset"
        assert datasets[0].team_id == team_id
        assert datasets[0].user_id == runtime._user_id
        assert datasets[0].experiment_id == exp.id
        assert datasets[0].run_id == run_obj.uuid
        assert datasets[0].path == f"{runtime.team_id}/dataset:{list_versions[0]}"
        assert datasets[0].meta is None
