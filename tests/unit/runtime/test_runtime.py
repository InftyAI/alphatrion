import uuid

import pytest

from alphatrion.runtime.runtime import global_runtime, init
from alphatrion.server import runtime

@pytest.mark.asyncio
async def test_project_without_team_id():
    team_id = uuid.uuid4()
    runtime.init()
    user_id = runtime.server_runtime().metadb.create_user(username="user1", email="user1@example.com", team_id=team_id)

    init(
        user_id=user_id,
    )

    assert global_runtime()._team_id == team_id
