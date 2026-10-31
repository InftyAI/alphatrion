import pytest
from pydantic import ValidationError

from alphatrion.swarm.tree import ScoreMode, Tree


def build_tree():
    tree = Tree()
    root = tree._set_score(tree.add("v0").id, 0.1)
    a = tree._set_score(tree.add("v1a", parent_id=root.id).id, 0.5)
    b = tree._set_score(tree.add("v1b", parent_id=root.id).id, 0.3)
    c = tree.add("v2a", parent_id=a.id)
    return tree, root, a, b, c


def test_structure():
    tree, root, a, b, c = build_tree()

    assert tree.root == root
    assert len(tree) == 4
    assert tree.children(root.id) == [a, b]
    assert tree.parent(c.id) == a
    assert tree.parent(root.id) is None
    assert tree.leaves() == [b, c]
    assert tree.lineage(c.id) == [root, a, c]
    assert tree.depth(c.id) == 2


def test_best():
    tree, root, a, _, c = build_tree()
    assert tree.best() == a
    assert tree.best(ScoreMode.MIN) == root

    tree._set_score(c.id, 0.9)
    assert tree.best() == c
    assert Tree().best() is None


def test_score_is_frozen():
    tree, root, *_ = build_tree()
    with pytest.raises(ValidationError):
        root.score = 1.0
    assert root.score == 0.1


def test_invalid_add():
    tree, *_ = build_tree()
    with pytest.raises(ValueError):
        tree.add("another root")
    with pytest.raises(KeyError):
        tree.add("orphan", parent_id="missing")


def test_save_and_load(tmp_path):
    tree, root, a, b, c = build_tree()
    path = tmp_path / "tree.json"
    tree.save(path)
    loaded = Tree.load(path)

    assert [x.id for x in loaded] == [root.id, a.id, b.id, c.id]
    assert loaded.lineage(c.id)[1].content == "v1a"
    assert loaded.best().id == a.id
