from abc import ABC, abstractmethod


class MetaStore(ABC):
    """Base class for all metadata storage backends."""

    @abstractmethod
    def get_project(self, project_id: str):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_exp(
        self,
        name: str,
        project_id: str,
        description: str | None = None,
        meta: dict | None = None,
    ) -> int:
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
    def get_exp_by_name(self, name: str, project_id: str):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_exps(self, project_id: str, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_model(
        self,
        name: str,
        project_id: str,
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_model(self, model_id: int, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_model(self, model_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_models(self, project_id: str, page: int, page_size: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_model(self, model_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_trial(
        self,
        project_id: str,
        experiment_id: str,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_trial(self, trial_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_trial_by_name(self, name: str, experiment_id: str):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_trial(self, trial_id: int, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_run(self, project_id: str, trial_id: str) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def create_metric(
        self,
        trial_id: str,
        name: str,
        value: float,
        step: int | None = None,
        timestamp: int | None = None,
    ) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list_metrics(self, trial_id: int) -> list[dict]:
        raise NotImplementedError("Subclasses must implement this method.")
