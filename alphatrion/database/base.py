from abc import ABC

class Database(ABC):
    """Base class for all databases."""
    def __init__(self):
        pass

    def create_exp(self, name: str, project_id: str, description: str | None, meta: dict | None):
        raise NotImplementedError("Subclasses must implement this method.")

    def delete_exp(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    def update_exp(self, exp_id: int, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_exp(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    def list_exps(self, project_id: str, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")
