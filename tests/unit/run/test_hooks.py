"""Tests for post-run hooks"""

import uuid
from unittest.mock import Mock, patch

import pytest

from alphatrion.run.hooks import PostRunHookFn
from alphatrion.storage.sql_models import Status
from alphatrion.storage.sqlstore import SQLStore


@pytest.fixture
def db():
    """Create in-memory database for testing"""
    db = SQLStore("sqlite:///:memory:", init_tables=True)
    yield db


def test_sync_metadata_with_dict_result(db):
    """Test sync_metadata hook with dict result"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with nested metadata structure
    result = {
        "metadata": {
            "accuracy": 0.95,
            "loss": 0.05,
            "num_epochs": 10,
        }
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_metadata(run_id, result)

        # Verify metadata was updated
        run = db.get_run(run_id)
        assert run.meta == result["metadata"]
        assert run.meta["accuracy"] == 0.95
        assert run.meta["loss"] == 0.05
        assert run.meta["num_epochs"] == 10


def test_sync_metadata_with_non_dict_result(db):
    """Test sync_metadata hook with non-dict result (should not update)"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result as non-dict
    result = "some string result"

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_metadata(run_id, result)

        # Verify metadata was not updated
        run = db.get_run(run_id)
        assert run.meta is None


def test_sync_metadata_merges_with_existing_metadata(db):
    """Test that sync_metadata merges with existing metadata"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Set initial metadata
    db.update_run(run_id=run_id, meta={"team": "ml-research", "experiment": "exp1"})

    # Mock result with nested metadata structure
    result = {
        "metadata": {
            "accuracy": 0.95,
            "loss": 0.05,
        }
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_metadata(run_id, result)

        # Verify metadata was merged, not replaced
        run = db.get_run(run_id)
        assert run.meta["team"] == "ml-research"
        assert run.meta["experiment"] == "exp1"
        assert run.meta["accuracy"] == 0.95
        assert run.meta["loss"] == 0.05


def test_custom_hook(db):
    """Test custom hook implementation"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Define custom hook
    def add_team_info(run_id, result):
        from alphatrion.runtime.runtime import global_runtime

        metadb = global_runtime().metadb
        metadb.update_run(run_id=run_id, meta={"team": "custom-team"})

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    # Patch where it's used (inside the function)
    with patch("alphatrion.runtime.runtime.global_runtime", return_value=mock_runtime):
        # Call custom hook
        add_team_info(run_id, {"some": "result"})

        # Verify metadata was updated
        run = db.get_run(run_id)
        assert run.meta["team"] == "custom-team"


def test_hook_signature():
    """Test that sync_metadata has correct signature"""
    import inspect

    sig = inspect.signature(PostRunHookFn.sync_metadata)
    params = list(sig.parameters.keys())

    # Should have exactly 2 parameters: run_id and result
    assert len(params) == 2
    assert params[0] == "run_id"
    assert params[1] == "result"


def test_sync_status_with_status_enum(db):
    """Test sync_status hook with Status enum"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with status as Status enum
    result = {
        "status": Status.COMPLETED,
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status was updated
        run = db.get_run(run_id)
        assert run.status == Status.COMPLETED


def test_sync_status_with_string(db):
    """Test sync_status hook with string status"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with status as string
    result = {
        "status": "COMPLETED",
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status was updated
        run = db.get_run(run_id)
        assert run.status == Status.COMPLETED


def test_sync_status_with_lowercase_string(db):
    """Test sync_status hook with string status"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with status as string
    result = {
        "status": "completed",  # lowercase string
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status was updated
        run = db.get_run(run_id)
        assert run.status == Status.COMPLETED


def test_sync_status_with_integer(db):
    """Test sync_status hook with integer status"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with status as integer
    result = {
        "status": 9,  # Status.COMPLETED
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status was updated
        run = db.get_run(run_id)
        assert run.status == Status.COMPLETED


def test_sync_status_with_invalid_string(db):
    """Test sync_status hook with invalid string status"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
        status=Status.RUNNING,
    )

    # Mock result with invalid status string
    result = {
        "status": "INVALID_STATUS",
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status was NOT updated
        run = db.get_run(run_id)
        assert run.status == Status.RUNNING  # Unchanged


def test_both_hooks_together(db):
    """Test sync_metadata and sync_status hooks working together"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with both metadata and status
    result = {
        "metadata": {
            "accuracy": 0.95,
            "loss": 0.05,
            "num_epochs": 10,
        },
        "status": "COMPLETED",
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call both hooks
        PostRunHookFn.sync_metadata(run_id, result)
        PostRunHookFn.sync_status(run_id, result)

        # Verify both metadata and status were updated
        run = db.get_run(run_id)
        assert run.meta["accuracy"] == 0.95
        assert run.meta["loss"] == 0.05
        assert run.meta["num_epochs"] == 10
        assert run.status == Status.COMPLETED


def test_sync_status_with_status_msg(db):
    """Test sync_status hook with status_msg"""
    org_id = uuid.uuid4()
    team_id = db.create_team(org_id=org_id, name="Test Team")
    user_id = db.create_user(
        org_id=org_id,
        name="tester",
        email="tester@example.com",
    )
    exp_id = db.create_experiment(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        name="test-exp",
    )
    run_id = db.create_run(
        org_id=org_id,
        team_id=team_id,
        user_id=user_id,
        experiment_id=exp_id,
    )

    # Mock result with status and status_msg
    result = {
        "status": "COMPLETED",
        "status_msg": "Training completed successfully",
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHookFn.sync_status(run_id, result)

        # Verify status and status_msg were updated
        run = db.get_run(run_id)
        assert run.status == Status.COMPLETED
        assert run.meta["status_msg"] == "Training completed successfully"
