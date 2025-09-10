from abc import ABC, abstractmethod

from alphatrion.runtime.runtime import Runtime


class Experiment(ABC):
    """Base class for all experiments."""

    def __init__(self, runtime: Runtime):
        self._runtime = runtime

    @abstractmethod
    def create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list(self, page: int = 0, page_size: int = 10):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_labels(self, exp_id: int, labels: dict):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def start(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def stop(self, exp_id: int, status: str = "finished"):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def status(self, exp_id: int) -> str:
        raise NotImplementedError("Subclasses must implement this method.")
