import os
import tempfile
import time

import pytest

import alphatrion as alpha
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.trial.trial import CheckpointConfig, TrialConfig, current_trial_id


@pytest.mark.asyncio
async def test_log_artifact():
    alpha.init(project_id="test_project", artifact_insecure=True)

    async with alpha.CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        trial = exp.start_trial(description="First trial")

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

        trial.stop()

        got_exp = exp._runtime._metadb.get_exp(exp_id=exp._id)
        assert got_exp is not None
        assert got_exp.name == "context_exp"

        got_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert got_trial is not None
        assert got_trial.description == "First trial"
        assert got_trial.status == TrialStatus.FINISHED


@pytest.mark.asyncio
async def test_log_params():
    alpha.init(project_id="test_project", artifact_insecure=True)

    async with alpha.CraftExperiment.run(name="test_experiment") as exp:
        trial = exp.start_trial(description="First trial", params={"param1": 0.1})

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

        trial.stop()

        trial = exp.start_trial(description="Second trial", params={"param1": 0.1})
        assert current_trial_id.get() == trial.id
        trial.stop()


@pytest.mark.asyncio
async def test_log_metrics():
    alpha.init(project_id="test_project", artifact_insecure=True)

    async with alpha.CraftExperiment.run(name="test_experiment") as exp:
        trial = exp.start_trial(description="First trial", params={"param1": 0.1})

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.1}

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 0

        await alpha.log_metrics({"accuracy": 0.95, "loss": 0.1})

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 2
        assert metrics[0].key == "accuracy"
        assert metrics[0].value == 0.95
        assert metrics[0].step == 1
        assert metrics[1].key == "loss"
        assert metrics[1].value == 0.1
        assert metrics[1].step == 1

        await alpha.log_metrics({"accuracy": 0.96})

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 3
        assert metrics[2].key == "accuracy"
        assert metrics[2].value == 0.96
        assert metrics[2].step == 2

        trial.stop()


@pytest.mark.asyncio
async def test_log_metrics_with_save_best_only():
    alpha.init(project_id="test_project", artifact_insecure=True)

    async with alpha.CraftExperiment.run(
        name="context_exp",
        description="Context manager test",
        meta={"key": "value"},
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            _ = exp.start_trial(
                description="Trial with save_best_only",
                config=TrialConfig(
                    checkpoint=CheckpointConfig(
                        enabled=True,
                        path=tmpdir,
                        save_on_best=True,
                        monitor_metric="accuracy",
                        monitor_mode="max",
                    )
                ),
            )

            file1 = "file1.txt"
            with open(file1, "w") as f:
                f.write("This is file1.")

            await alpha.log_metrics({"accuracy": 0.90})

            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            # To avoid the same timestamp hash, we wait for 1 second
            time.sleep(1)

            await alpha.log_metrics({"accuracy": 0.78})
            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 1

            time.sleep(1)

            await alpha.log_metrics({"accuracy": 0.91})
            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 2

            time.sleep(1)

            await alpha.log_metrics({"accuracy2": 0.98})
            versions = exp._runtime._artifact.list_versions(exp.id)
            assert len(versions) == 2
