import pytest

from alphatrion.runtime.runtime import global_runtime, init
from alphatrion.storage import runtime


@pytest.mark.asyncio
async def test_init_without_team_id():
    import uuid

    runtime.init()
    org_id = uuid.uuid4()
    team_id = runtime.storage_runtime().metadb.create_team(org_id=org_id, name="team1")
    # Use unique email for each test run
    unique_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
    user_id = runtime.storage_runtime().metadb.create_user(
        org_id=org_id, name="user1", email=unique_email, team_id=team_id
    )

    init(user_id=user_id)
    assert global_runtime()._team_id == team_id
