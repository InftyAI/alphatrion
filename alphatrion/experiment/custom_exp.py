from datetime import datetime

from alphatrion.artifact.artifact import Artifact
from alphatrion.experiment.base import Experiment
from alphatrion.metadata.sql_models import COMPLETED_STATUS, ExperimentStatus
from alphatrion.runtime.runtime import Runtime


class CustomExperiment(Experiment):
    def __init__(self, runtime: Runtime):
        super().__init__(runtime)
        self._artifact = Artifact(runtime)

    def create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        self._runtime._metadb.create_exp(
            name=name,
            description=description,
            project_id=self._runtime._project_id,
            meta=meta,
            labels=labels,
        )

    def delete(self, exp_id: int):
        self._runtime._metadb.delete_exp(exp_id=exp_id)
        # TODO: delete related artifacts too. But for google artifact registry,
        # it seems not supported to delete a tag only.
        # See issue: https://github.com/InftyAI/alphatrion/issues/14

    def get(self, exp_id: int):
        return self._runtime._metadb.get_exp(exp_id=exp_id)

    def list(self, page: int = 0, page_size: int = 10):
        return self._runtime._metadb.list_exps(
            project_id=self._runtime._project_id, page=page, page_size=page_size
        )

    # Please provide all the labels to update, or it will overwrite the existing labels.
    def update_labels(self, exp_id: int, labels: dict):
        self._runtime._metadb.update_exp(exp_id=exp_id, labels=labels)

    # start for experiment usually means update the status to running.
    def start(self, exp_id: int):
        self._runtime._metadb.update_exp(exp_id=exp_id, status=ExperimentStatus.RUNNING)

    # stop for experiment usually means update the status to finished or failed.
    def stop(self, exp_id: int, status: ExperimentStatus = ExperimentStatus.FINISHED):
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        if exp is not None and exp.status not in COMPLETED_STATUS:
            duration = (datetime.now() - exp.created_at).total_seconds()
            self._runtime._metadb.update_exp(
                exp_id=exp_id, status=status, duration=duration
            )

    def status(self, exp_id: int) -> ExperimentStatus:
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        return exp.status

    def save_checkpoint(self, exp_id: int, meta: dict | None = None):
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        self._artifact.push(
            experiment_name=exp.name, files=[self._runtime._checkpoint_path]
        )
