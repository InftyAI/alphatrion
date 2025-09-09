import pytest

from alphatrion.metadata.base import MetaStore

def test_metadata_abstract_methods():
    db = MetaStore()

    with pytest.raises(NotImplementedError):
        db.create_exp("test", "test", "test", {})

    with pytest.raises(NotImplementedError):
        db.delete_exp(1)

    with pytest.raises(NotImplementedError):
        db.update_exp(1)

    with pytest.raises(NotImplementedError):
        db.get_exp(1)

    with pytest.raises(NotImplementedError):
        db.list_exps("test", 1, 10)
