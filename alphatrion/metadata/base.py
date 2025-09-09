from abc import ABC, abstractmethod


class MetaStore(ABC):
    """Base class for all metadata storage backends."""

    @abstractmethod
    def create_exp(
        self, name: str, project_id: str, description: str | None, meta: dict | None
    ):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_exp(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_exp(self, exp_id: int, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_exp(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_exps(self, project_id: str, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")
