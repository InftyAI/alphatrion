"""Tests for post-run hooks"""

import uuid
from unittest.mock import Mock, patch

import pytest

from alphatrion.run.hooks import PostRunHooks
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

    # Mock result as dict
    result = {
        "accuracy": 0.95,
        "loss": 0.05,
        "num_epochs": 10,
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHooks.sync_metadata(run_id, result)

        # Verify metadata was updated
        run = db.get_run(run_id)
        assert run.meta == result
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
        PostRunHooks.sync_metadata(run_id, result)

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

    # Mock result
    result = {
        "accuracy": 0.95,
        "loss": 0.05,
    }

    # Mock global_runtime
    mock_runtime = Mock()
    mock_runtime.metadb = db

    with patch("alphatrion.run.hooks.global_runtime", return_value=mock_runtime):
        # Call the hook
        PostRunHooks.sync_metadata(run_id, result)

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

    sig = inspect.signature(PostRunHooks.sync_metadata)
    params = list(sig.parameters.keys())

    # Should have exactly 2 parameters: run_id and result
    assert len(params) == 2
    assert params[0] == "run_id"
    assert params[1] == "result"
