import os
import tempfile

import alphatrion as alpha
from alphatrion.metadata.sql_models import TrialStatus
from alphatrion.trial.trial import current_trial_id


def test_log_artifact():
    alpha.init(project_id="test_project", artifact_insecure=True)

    with alpha.CraftExperiment.run(
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

            alpha.log_artifact(paths="file1.txt", version="v1")
            versions = exp._runtime._artifact.list_versions(
                exp_obj.uuid
            )
            assert "v1" in versions

            with open("file1.txt", "w") as f:
                f.write("This is modified file1.")

            # push folder instead
            alpha.log_artifact(paths=["file1.txt"], version="v2")
            versions = exp._runtime._artifact.list_versions(
                exp_obj.uuid
            )
            assert "v2" in versions

        exp._runtime._artifact.delete(
            repo_name=exp_obj.uuid,
            versions=["v1", "v2"],
        )
        versions = exp._runtime._artifact.list_versions(exp_obj.uuid)
        assert len(versions) == 0

        trial.finish()

        got_exp = exp._runtime._metadb.get_exp(exp_id=exp._id)
        assert got_exp is not None
        assert got_exp.name == "context_exp"

        got_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert got_trial is not None
        assert got_trial.description == "First trial"
        assert got_trial.status == TrialStatus.FINISHED


def test_log_params():
    alpha.init(project_id="test_project", artifact_insecure=True)

    with alpha.CraftExperiment.run(name="test_experiment") as exp:
        trial = exp.start_trial(description="First trial", params={"param1": 0.1})

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.1}

        params = {"param1": 0.2}
        alpha.log_params(params=params)

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.2}
        assert new_trial.status == TrialStatus.RUNNING
        assert current_trial_id.get() == trial._id

        trial.finish()

        trial = exp.start_trial(description="Second trial", params={"param1": 0.1})
        assert current_trial_id.get() == trial._id
        trial.finish()


def test_log_metrics():
    alpha.init(project_id="test_project", artifact_insecure=True)

    with alpha.CraftExperiment.run(name="test_experiment") as exp:
        trial = exp.start_trial(description="First trial", params={"param1": 0.1})

        new_trial = exp._runtime._metadb.get_trial(trial_id=trial._id)
        assert new_trial is not None
        assert new_trial.params == {"param1": 0.1}

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 0

        alpha.log_metrics({"accuracy": 0.95, "loss": 0.1})

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 2
        assert metrics[0].key == "accuracy"
        assert metrics[0].value == 0.95
        assert metrics[0].step == 1
        assert metrics[1].key == "loss"
        assert metrics[1].value == 0.1
        assert metrics[1].step == 1

        alpha.log_metrics({"accuracy": 0.96})

        metrics = exp._runtime._metadb.list_metrics(trial_id=trial._id)
        assert len(metrics) == 3
        assert metrics[2].key == "accuracy"
        assert metrics[2].value == 0.96
        assert metrics[2].step == 2

        trial.finish()
