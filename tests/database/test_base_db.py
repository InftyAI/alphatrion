import pytest

from alphatrion.database.base import Database

def test_database_abstract_methods():
    db = Database()

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
