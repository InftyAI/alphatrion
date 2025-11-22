import uuid
from abc import ABC, abstractmethod

from alphatrion.metadata.sql_models import Model, Trial


class MetaStore(ABC):
    """Base class for all metadata storage backends."""

    @abstractmethod
    def get_project(self, project_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_exp(
        self,
        name: str,
        project_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_exp(self, exp_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_exp(self, exp_id: uuid.UUID, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_exp(self, exp_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_exp_by_name(self, name: str, project_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_exps(self, project_id: uuid.UUID, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_model(
        self,
        name: str,
        project_id: uuid.UUID,
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_model(self, model_id: uuid.UUID, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_model(self, model_id: uuid.UUID) -> Model | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_models(self, project_id: uuid.UUID, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_model(self, model_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_trial(
        self,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_trial(self, trial_id: uuid.UUID) -> Trial | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_trial_by_name(self, name: str, experiment_id: uuid.UUID) -> Trial | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_trial(self, trial_id: uuid.UUID, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_run(
        self,
        project_id: uuid.UUID,
        trial_id: uuid.UUID,
        experiment_id: uuid.UUID,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_metric(
        self,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        trial_id: uuid.UUID,
        run_id: uuid.UUID,
        key: str,
        value: float,
        step: int | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_metrics_by_trial_id(self, trial_id: uuid.UUID) -> list[dict]:
        raise NotImplementedError("Subclasses must implement this method.")
