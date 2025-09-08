from alphatrion.database.sql_models import ExperimentStatus
from alphatrion.experiment.base import Experiment
from alphatrion.runtime.runtime import Runtime


class CustomExperiment(Experiment):
    def __init__(self, runtime: Runtime):
        super().__init__(runtime)

    def create(self, name: str, description: str | None = None, meta: dict | None = None):
        self._runtime._metadb.create_exp(name=name, description=description, project_id=self._runtime._project_id, meta=meta)

    def delete(self, exp_id: int):
        self._runtime._metadb.delete_exp(exp_id=exp_id)

    def get(self, exp_id: int):
        return self._runtime._metadb.get_exp(exp_id=exp_id)

    # start for experiment usually means update the status to running.
    def start(self, exp_id: int):
        self._runtime._metadb.update_exp(exp_id=exp_id, status=ExperimentStatus.RUNNING)

    # stop for experiment usually means update the status to finished or failed.
    def stop(self, exp_id: int, status: ExperimentStatus = ExperimentStatus.FINISHED):
        self._runtime._metadb.update_exp(exp_id=exp_id, status=status)

    def status(self, exp_id: int) -> ExperimentStatus:
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        return exp.status
