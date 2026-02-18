import uuid

import pytest
from dotenv import load_dotenv

# Load environment variables first
load_dotenv(dotenv_path=".env.integration-test")


@pytest.fixture(scope="session", autouse=True)
def init_runtime():
    """Initialize runtime for all integration tests"""
    import alphatrion
    from alphatrion.storage import runtime

    # Initialize storage runtime first to create user and team
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Use fixed UUIDs for test user and team to avoid conflicts
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    team_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Create test team if it doesn't exist
    try:
        existing_team = metadb.get_team(team_id=team_id)
        if not existing_team:
            metadb.create_team(uuid=team_id, name="test_team", description="Test team")
    except Exception:
        metadb.create_team(uuid=team_id, name="test_team", description="Test team")

    # Create test user if it doesn't exist
    try:
        existing_user = metadb.get_user(user_id=user_id)
        if not existing_user:
            metadb.create_user(
                uuid=user_id,
                username="test_user",
                email="test@example.com",
                team_id=team_id,
            )
    except Exception:
        pass  # User already exists

    # Now initialize alphatrion runtime with the test user
    alphatrion.init(user_id=user_id, team_id=team_id)
    yield
    # Cleanup if needed
