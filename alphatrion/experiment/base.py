from abc import ABC, abstractmethod
from dataclasses import dataclass

from alphatrion.runtime.runtime import global_runtime
from alphatrion.trial import trial


@dataclass
class Experiment(ABC):
    """
    Base Experiment class. One instance one experiment, multiple trials.
    """

    __slots__ = ("_runtime", "_id", "_trials")

    def __init__(self):
        self._runtime = global_runtime()
        # All trials in this experiment, key is trial_id, value is Trial instance.
        self._trials = dict()

    def _reset(self):
        self._trials = dict()
        self._exp = None

    def __enter__(self):
        if self._id is None:
            raise RuntimeError("Experiment is not set. Did you call begin()?")

        exp = self._get()
        if exp is None:
            raise RuntimeError(f"Experiment {self._id} not found in the database.")

        self._runtime.current_exp_uuid = exp.uuid
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._reset()
        self._runtime.current_exp_uuid = None

    @classmethod
    @abstractmethod
    def run(
        cls, name: str, description: str | None = None, meta: dict | None = None
    ) -> "Experiment":
        """Return a new experiment."""
        ...

    def _register_trial(self, id: int, instance: trial.Trial):
        self._trials[id] = instance

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

    def delete(self):
        exp = self._get()
        if exp is None:
            return

        self._runtime._metadb.delete_exp(exp_id=self._exp.id)
        # TODO: Should we make this optional as a parameter?
        tags = self._runtime._artifact.list_versions(repo_name=str(self._exp.id))
        self._runtime._artifact.delete(experiment_name=exp.name, versions=tags)
