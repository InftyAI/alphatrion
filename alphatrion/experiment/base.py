import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel, Field

from alphatrion.runtime.runtime import global_runtime
from alphatrion.trial import trial


class ExperimentConfig(BaseModel):
    """
    Configuration for Experiment.
    """

    max_runtime_seconds: int = Field(
        default=-1,
        description="Maximum runtime seconds for the experiment. \
        It will overwrite the trial timeout if both are set. \
        Default is -1 (no limit).",
    )


@dataclass
class Experiment(ABC):
    """
    Base Experiment class. One instance one experiment, multiple trials.
    """

    __slots__ = ("_runtime", "_id", "_trials")

    def __init__(self, config: ExperimentConfig | None = None):
        self._config = config or ExperimentConfig()
        self._runtime = global_runtime()
        # All trials in this experiment, key is trial_id, value is Trial instance.
        self._trials = dict()
        self._runtime.current_exp = self

    @property
    def id(self):
        return self._id

    def get_trial(self, id: int) -> trial.Trial | None:
        return self._trials.get(id)

    async def __aenter__(self):
        if self._id is None:
            raise RuntimeError("Experiment is not set. Did you call start()?")

        exp = self._get()
        if exp is None:
            raise RuntimeError(f"Experiment {self._id} not found in the database.")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._trials = dict()
        self._runtime.current_exp = None

    @classmethod
    @abstractmethod
    def setup(
        cls, name: str, description: str | None = None, meta: dict | None = None
    ) -> "Experiment":
        """Return a new experiment."""
        ...

    def register_trial(self, id: uuid.UUID, instance: trial.Trial):
        self._trials[id] = instance

    def unregister_trial(self, id: uuid.UUID):
        self._trials.pop(id, None)

    def _create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
    ):
        """
        :param name: the name of the experiment.
        :param description: the description of the experiment
        :param meta: the metadata of the experiment

        :return: the experiment ID
        """

        self._id = self._runtime._metadb.create_exp(
            name=name,
            description=description,
            project_id=self._runtime._project_id,
            meta=meta,
        )
        return self._id

    def _get(self):
        return self._runtime._metadb.get_exp(exp_id=self._id)

    def _get_by_name(self, name: str, project_id: str):
        return self._runtime._metadb.get_exp_by_name(name=name, project_id=project_id)

    def delete(self):
        exp = self._get()
        if exp is None:
            return

        self._runtime._metadb.delete_exp(exp_id=self._exp.id)
        # TODO: Should we make this optional as a parameter?
        tags = self._runtime._artifact.list_versions(repo_name=str(self._exp.id))
        self._runtime._artifact.delete(experiment_name=exp.name, versions=tags)
