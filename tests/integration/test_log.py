import asyncio
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta

import pytest

import alphatrion as alpha
from alphatrion.experiment.experiment import current_exp_id
from alphatrion.log.log import ARTIFACT_PATH
from alphatrion.metadata.sql_models import Status


@pytest.mark.asyncio
async def test_log_artifact():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with alpha.Project.setup(
        name="log_artifact_project",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        exp = proj.start_experiment(name="first-exp")

        proj_obj = proj._runtime._metadb.get_project(project_id=proj._id)
        assert proj_obj is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            await alpha.log_artifact(paths="file1.txt", version="v1")
            versions = exp._runtime._artifact.list_versions(proj_obj.uuid)
            assert "v1" in versions

            with open("file1.txt", "w") as f:
                f.write("This is modified file1.")

            # push folder instead
            await alpha.log_artifact(paths=["file1.txt"], version="v2")
            versions = exp._runtime._artifact.list_versions(proj_obj.uuid)
            assert "v2" in versions

        exp._runtime._artifact.delete(
            repo_name=proj_obj.uuid,
            versions=["v1", "v2"],
        )
        versions = exp._runtime._artifact.list_versions(proj_obj.uuid)
        assert len(versions) == 0

        exp.done()

        got_proj = proj._runtime._metadb.get_project(project_id=proj._id)
        assert got_proj is not None
        assert got_proj.name == "log_artifact_project"

        got_exp = proj._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert got_exp is not None
        assert got_exp.name == "first-exp"
        assert got_exp.status == Status.COMPLETED


@pytest.mark.asyncio
async def test_log_params():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async with alpha.Project.setup(name="log_params_proj") as proj:
        exp = proj.start_experiment(name="first-exp", params={"param1": 0.1})

        new_exp = proj._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.1}

        params = {"param1": 0.2}
        await alpha.log_params(params=params)

        new_exp = exp._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.2}
        assert new_exp.status == Status.RUNNING
        assert current_exp_id.get() == exp.id

        exp.done()

        exp = proj.start_experiment(name="second-exp", params={"param1": 0.1})
        assert current_exp_id.get() == exp.id
        exp.done()


@pytest.mark.asyncio
async def test_log_metrics():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def log_metric(metrics: dict):
        await alpha.log_metrics(metrics)

    async with alpha.Project.setup(name="log_metrics_exp") as proj:
        exp = proj.start_experiment(name="first-exp", params={"param1": 0.1})

        new_exp = exp._runtime._metadb.get_experiment(experiment_id=exp.id)
        assert new_exp is not None
        assert new_exp.params == {"param1": 0.1}

        metrics = proj._runtime._metadb.list_metrics_by_experiment_id(
            experiment_id=exp.id
        )
        assert len(metrics) == 0

        run = exp.start_run(lambda: log_metric({"accuracy": 0.95, "loss": 0.1}))
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

        run = exp.start_run(lambda: log_metric({"accuracy": 0.96}))
        await run.wait()

        metrics = proj._runtime._metadb.list_metrics_by_experiment_id(
            experiment_id=exp.id
        )
        assert len(metrics) == 3
        assert metrics[2].key == "accuracy"
        assert metrics[2].value == 0.96
        run_id_2 = metrics[2].run_id
        assert run_id_2 is not None
        assert run_id_2 != run_id_1

        exp.done()


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_max():
    team_id = uuid.uuid4()
    alpha.init(team_id=team_id, artifact_insecure=True, init_tables=True)

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    def find_unused_version(used_versions, all_versions):
        for v in all_versions:
            if v not in used_versions:
                return v
        return None

    async with alpha.Project.setup(
        name="log_metrics_with_save_on_max",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            file = "file.txt"

            def pre_save_hook():
                with open(file, "a") as f:
                    f.write("This is pre_save_hook modified file.\n")

            exp = proj.start_experiment(
                name="exp-with-save_on_best",
                config=alpha.ExperimentConfig(
                    checkpoint=alpha.CheckpointConfig(
                        enabled=True,
                        path=tmpdir,
                        save_on_best=True,
                        pre_save_hook=pre_save_hook,
                    ),
                    monitor_metric="accuracy",
                    # Make sure raw max also works.
                    monitor_mode="max",
                ),
            )

            with open(file, "w") as f:
                f.write("This is file.\n")

            run = exp.start_run(lambda: log_metric(0.90))
            await run.wait()

            # We need this because the returned version is unordered.
            used_version = []

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 1
            run_obj = run._get_obj()
            fixed_version = versions[0]
            used_version.append(fixed_version)
            assert (
                run_obj.meta[ARTIFACT_PATH] == f"{team_id}/{proj.id}:" + fixed_version
            )
            with open(file) as f:
                assert len(f.readlines()) == 2

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = exp.start_run(lambda: log_metric(0.78))
            await run.wait()

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 1

            time.sleep(1)

            run = exp.start_run(lambda: log_metric(0.91))
            await run.wait()

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 2

            fixed_version = find_unused_version(used_version, versions)
            used_version.append(fixed_version)
            run_obj = run._get_obj()
            assert (
                run_obj.meta[ARTIFACT_PATH] == f"{team_id}/{proj.id}:" + fixed_version
            )

            with open(file) as f:
                assert len(f.readlines()) == 3

            time.sleep(1)

            run = exp.start_run(lambda: log_metric(0.98))
            await run.wait()

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 3
            run_obj = run._get_obj()

            fixed_version = find_unused_version(used_version, versions)
            used_version.append(fixed_version)
            assert (
                run_obj.meta[ARTIFACT_PATH] == f"{team_id}/{proj.id}:" + fixed_version
            )
            with open(file) as f:
                assert len(f.readlines()) == 4

            exp.done()


@pytest.mark.asyncio
async def test_log_metrics_with_save_on_min():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def log_metric(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(
        name="log_metrics_with_save_on_min",
        description="Context manager test",
        meta={"key": "value"},
    ) as proj:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            exp = proj.start_experiment(
                name="exp-with-save_on_best",
                config=alpha.ExperimentConfig(
                    checkpoint=alpha.CheckpointConfig(
                        enabled=True,
                        path=tmpdir,
                        save_on_best=True,
                    ),
                    monitor_metric="accuracy",
                    monitor_mode=alpha.MonitorMode.MIN,
                ),
            )

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            run = exp.start_run(lambda: log_metric(0.30))
            await run.wait()

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 1

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            run = exp.start_run(lambda: log_metric(0.58))
            await run.wait()

            versions = proj._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 1

            time.sleep(1)

            run = exp.start_run(lambda: log_metric(0.21))
            await run.wait()

            versions = exp._runtime._artifact.list_versions(proj.id)
            assert len(versions) == 2

            time.sleep(1)

            task = exp.start_run(lambda: log_metric(0.18))
            await task.wait()
            versions = proj._runtime._artifact.list_versions(str(proj.id))
            assert len(versions) == 3

            exp.done()


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(100)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(name="log_metrics_with_early_stopping") as proj:
        async with proj.start_experiment(
            name="exp-with-early-stopping",
            config=alpha.ExperimentConfig(
                monitor_metric="accuracy",
                early_stopping_runs=2,
            ),
        ) as exp:
            exp.start_run(lambda: fake_work(0.5))
            exp.start_run(lambda: fake_work(0.6))
            exp.start_run(lambda: fake_work(0.2))
            exp.start_run(lambda: fake_work(0.7))
            exp.start_run(lambda: fake_sleep(0.2))
            # The first run that is worse than 0.6
            exp.start_run(lambda: fake_work(0.4))
            # The second run that is worse than 0.6, should trigger early stopping
            exp.start_run(lambda: fake_work(0.1))
            exp.start_run(lambda: fake_work(0.2))
            # trigger early stopping
            await exp.wait()

            assert (
                len(
                    exp._runtime._metadb.list_metrics_by_experiment_id(
                        experiment_id=exp.id
                    )
                )
                == 6
            )


@pytest.mark.asyncio
async def test_log_metrics_with_early_stopping_never_triggered():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(value)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(
        name="log_metrics_with_both_early_stopping_and_timeout"
    ) as proj:
        async with proj.start_experiment(
            name="exp-with-early-stopping",
            config=alpha.ExperimentConfig(
                monitor_metric="accuracy",
                early_stopping_runs=3,
                max_execution_seconds=3,
            ),
        ) as exp:
            start_time = datetime.now()
            exp.start_run(lambda: fake_work(1))
            exp.start_run(lambda: fake_work(2))
            exp.start_run(lambda: fake_sleep(2))
            # running in parallel.
            await exp.wait()

            assert (
                len(
                    exp._runtime._metadb.list_metrics_by_experiment_id(
                        experiment_id=exp.id
                    )
                )
                == 3
            )
            assert datetime.now() - start_time >= timedelta(seconds=3)


@pytest.mark.asyncio
async def test_log_metrics_with_max_run_number():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(name="log_metrics_with_max_run_number") as proj:
        async with proj.start_experiment(
            name="exp-with-max-run-number",
            config=alpha.ExperimentConfig(
                monitor_metric="accuracy",
                max_runs_per_experiment=5,
            ),
        ) as exp:
            while not exp.is_done():
                run = exp.start_run(lambda: fake_work(1))
                await run.wait()

            assert (
                len(
                    exp._runtime._metadb.list_metrics_by_experiment_id(
                        experiment_id=exp.id
                    )
                )
                == 5
            )


@pytest.mark.asyncio
async def test_log_metrics_with_max_target_meet():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(10)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(name="log_metrics_with_max_target_meet") as proj:
        async with proj.start_experiment(
            name="exp-with-max-target-meet",
            config=alpha.ExperimentConfig(
                monitor_metric="accuracy",
                target_metric_value=0.9,
            ),
        ) as exp:
            exp.start_run(lambda: fake_work(0.5))
            exp.start_run(lambda: fake_work(0.3))
            exp.start_run(lambda: fake_sleep(0.4))
            exp.start_run(lambda: fake_work(0.9))
            await exp.wait()

            assert (
                len(
                    exp._runtime._metadb.list_metrics_by_experiment_id(
                        experiment_id=exp.id
                    )
                )
                == 3
            )


@pytest.mark.asyncio
async def test_log_metrics_with_min_target_meet():
    alpha.init(team_id=uuid.uuid4(), artifact_insecure=True, init_tables=True)

    async def fake_work(value: float):
        await alpha.log_metrics({"accuracy": value})

    async def fake_sleep(value: float):
        await asyncio.sleep(3)
        await alpha.log_metrics({"accuracy": value})

    async with alpha.Project.setup(name="log_metrics_with_min_target_meet") as proj:
        async with proj.start_experiment(
            name="exp-with-min-target-meet",
            config=alpha.ExperimentConfig(
                monitor_metric="accuracy",
                target_metric_value=0.2,
                monitor_mode=alpha.MonitorMode.MIN,
            ),
        ) as exp:
            exp.start_run(lambda: fake_work(0.5))
            exp.start_run(lambda: fake_work(0.3))
            exp.start_run(lambda: fake_sleep(0.4))
            exp.start_run(lambda: fake_work(0.2))
            await exp.wait()

            assert (
                len(
                    exp._runtime._metadb.list_metrics_by_experiment_id(
                        experiment_id=exp.id
                    )
                )
                == 3
            )
