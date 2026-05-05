"""Integration tests for post-run hooks"""

import asyncio
import uuid

import pytest

import alphatrion as alpha
from alphatrion.experiment import CraftExperiment, ExperimentConfig
from alphatrion.run import PostRunHookFn
from alphatrion.runtime.runtime import global_runtime


@pytest.fixture
def test_org_id():
    return uuid.uuid4()


@pytest.fixture
def test_team_id():
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_run_hook_sync_metadata(test_org_id, test_user_id, test_team_id):
    """Test sync_metadata hook updates run metadata"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    async def train_model():
        """Function that returns metrics as dict"""
        await asyncio.sleep(0.1)
        return {
            "accuracy": 0.95,
            "loss": 0.05,
            "learning_rate": 0.001,
            "num_epochs": 10,
        }

    async with CraftExperiment.start("test_hook_experiment") as exp:
        # Create run with sync_metadata hook
        run = exp.run(train_model, post_run_hooks=[PostRunHookFn.sync_metadata])
        await exp.wait()

        # Verify run completed
        assert run.result is not None

        # Verify metadata was synced from result
        metadb = global_runtime().metadb
        run_obj = metadb.get_run(run_id=run.id)

        assert run_obj.meta is not None
        assert run_obj.meta["accuracy"] == 0.95
        assert run_obj.meta["loss"] == 0.05
        assert run_obj.meta["learning_rate"] == 0.001
        assert run_obj.meta["num_epochs"] == 10


@pytest.mark.asyncio
async def test_run_hook_with_non_dict_result(test_org_id, test_user_id, test_team_id):
    """Test sync_metadata hook with non-dict result doesn't update metadata"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    async def task_with_string_result():
        """Function that returns non-dict"""
        await asyncio.sleep(0.1)
        return "completed successfully"

    async with CraftExperiment.start("test_hook_non_dict") as exp:
        run = exp.run(
            task_with_string_result, post_run_hooks=[PostRunHookFn.sync_metadata]
        )
        await exp.wait()

        # Verify metadata was not updated
        metadb = global_runtime().metadb
        run_obj = metadb.get_run(run_id=run.id)

        # Metadata should be None or empty (hook didn't update it)
        assert run_obj.meta is None or run_obj.meta == {}


@pytest.mark.asyncio
async def test_experiment_level_hooks(test_org_id, test_user_id, test_team_id):
    """Test hooks configured at experiment level apply to all runs"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    async def task1():
        await asyncio.sleep(0.1)
        return {"task": "task1", "accuracy": 0.92}

    async def task2():
        await asyncio.sleep(0.1)
        return {"task": "task2", "accuracy": 0.94}

    # Configure experiment with sync_metadata hook
    config = ExperimentConfig(post_run_hooks=[PostRunHookFn.sync_metadata])

    async with CraftExperiment.start("test_exp_hooks", config=config) as exp:
        run1 = exp.run(task1)
        run2 = exp.run(task2)
        await exp.wait()

        # Verify both runs have metadata synced
        metadb = global_runtime().metadb

        run1_obj = metadb.get_run(run_id=run1.id)
        assert run1_obj.meta["task"] == "task1"
        assert run1_obj.meta["accuracy"] == 0.92

        run2_obj = metadb.get_run(run_id=run2.id)
        assert run2_obj.meta["task"] == "task2"
        assert run2_obj.meta["accuracy"] == 0.94


@pytest.mark.asyncio
async def test_custom_hook(test_org_id, test_user_id, test_team_id):
    """Test custom hook implementation"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    def add_custom_info(run_id, result):
        """Custom hook that adds extra metadata"""
        from alphatrion.runtime.runtime import global_runtime

        metadb = global_runtime().metadb
        metadb.update_run(
            run_id=run_id,
            meta={
                "team": "ml-research",
                "project": "image-classification",
                "custom_tag": "experimental",
            },
        )

    async def train_model():
        await asyncio.sleep(0.1)
        return {"accuracy": 0.95}

    async with CraftExperiment.start("test_custom_hook") as exp:
        # Use both built-in and custom hooks
        run = exp.run(
            train_model, post_run_hooks=[PostRunHookFn.sync_metadata, add_custom_info]
        )
        await exp.wait()

        # Verify both hooks ran
        metadb = global_runtime().metadb
        run_obj = metadb.get_run(run_id=run.id)

        # From sync_metadata hook
        assert run_obj.meta["accuracy"] == 0.95

        # From custom hook
        assert run_obj.meta["team"] == "ml-research"
        assert run_obj.meta["project"] == "image-classification"
        assert run_obj.meta["custom_tag"] == "experimental"


@pytest.mark.asyncio
async def test_hook_merges_with_existing_metadata(
    test_org_id, test_user_id, test_team_id
):
    """Test that hooks merge with existing metadata"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    async def train_model():
        await asyncio.sleep(0.1)
        return {"accuracy": 0.96, "loss": 0.04}

    async with CraftExperiment.start("test_merge_metadata") as exp:
        run = exp.run(train_model, post_run_hooks=[PostRunHookFn.sync_metadata])

        # Manually add some metadata before run completes
        metadb = global_runtime().metadb
        metadb.update_run(
            run_id=run.id, meta={"experiment_version": "v2", "notes": "test run"}
        )

        await exp.wait()

        # Verify metadata was merged, not replaced
        run_obj = metadb.get_run(run_id=run.id)

        # Original metadata preserved
        assert run_obj.meta["experiment_version"] == "v2"
        assert run_obj.meta["notes"] == "test run"

        # New metadata from hook added
        assert run_obj.meta["accuracy"] == 0.96
        assert run_obj.meta["loss"] == 0.04


@pytest.mark.asyncio
async def test_hook_failure_does_not_crash_run(test_org_id, test_user_id, test_team_id):
    """Test that hook failure doesn't crash the run"""
    alpha.init(org_id=test_org_id, team_id=test_team_id, user_id=test_user_id)

    def buggy_hook(run_id, result):
        """Hook that raises an exception"""
        raise ValueError("Intentional error for testing")

    async def train_model():
        await asyncio.sleep(0.1)
        return {"accuracy": 0.95}

    async with CraftExperiment.start("test_hook_failure") as exp:
        run = exp.run(
            train_model, post_run_hooks=[buggy_hook, PostRunHookFn.sync_metadata]
        )
        await exp.wait()

        # Run should still complete successfully
        assert run.result is not None

        # sync_metadata hook should still run and update metadata
        metadb = global_runtime().metadb
        run_obj = metadb.get_run(run_id=run.id)
        assert run_obj.meta["accuracy"] == 0.95
