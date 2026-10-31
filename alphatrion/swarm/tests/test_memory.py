from alphatrion.swarm.memory import Memory


def test_history_filters():
    memory = Memory()
    memory.record(0, "propose", "action", {"output": 1})
    memory.record(1, "check", "guardrail")
    memory.record(2, "propose", "action", {"output": 2})

    assert len(memory) == 3
    assert [e.step for e in memory.history(node="propose")] == [0, 2]
    assert [e.node for e in memory.history(type="guardrail")] == ["check"]
    assert [e.step for e in memory.history(last=2)] == [1, 2]
    assert memory.history(last=0) == []


def test_values():
    memory = Memory()
    assert memory.get("feedback", "none") == "none"
    memory.set("feedback", "too long")
    assert "feedback" in memory
    assert memory.get("feedback") == "too long"


def test_save_and_load(tmp_path):
    memory = Memory()
    memory.record(0, "propose", "action", {"output": object()})
    memory.set("iteration", 1)

    path = tmp_path / "memory.json"
    memory.save(path)
    loaded = Memory.load(path)

    assert len(loaded) == 1
    assert loaded.history()[0].node == "propose"
    assert isinstance(loaded.history()[0].data["output"], str)
    assert loaded.get("iteration") == 1
