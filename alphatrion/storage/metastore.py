import uuid
from abc import ABC, abstractmethod

from alphatrion.storage.sql_models import Experiment, Model, User


class MetaStore(ABC):
    """Base class for all metadata storage backends."""

    @abstractmethod
    def create_team(
        self, name: str, description: str | None = None, meta: dict | None = None
    ) -> uuid.UUID:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_team(self, team_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_user(
        self,
        username: str,
        email: str,
        team_id: uuid.UUID,
        meta: dict | None = None,
    ) -> uuid.UUID:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_user(self, user_id: uuid.UUID) -> User | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_users(
        self, team_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[User]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_project(
        self,
        name: str,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_project(self, project_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_project(self, project_id: uuid.UUID, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_project(self, project_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_proj_by_name(self, name: str, team_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_projects(self, team_id: uuid.UUID, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_model(
        self,
        name: str,
        team_id: uuid.UUID,
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
    def list_models(self, team_id: uuid.UUID, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_model(self, model_id: uuid.UUID):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_experiment(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_experiment(self, exp_id: uuid.UUID) -> Experiment | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_exp_by_name(self, name: str, project_id: uuid.UUID) -> Experiment | None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_experiment(self, experiment_id: uuid.UUID, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_run(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_metric(
        self,
        team_id: uuid.UUID,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        run_id: uuid.UUID,
        key: str,
        value: float,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_metrics_by_experiment_id(self, experiment_id: uuid.UUID) -> list[dict]:
        raise NotImplementedError("Subclasses must implement this method.")
