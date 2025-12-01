import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.metadata.base import MetaStore
from alphatrion.metadata.sql_models import (
    Base,
    Experiment,
    Metric,
    Model,
    Project,
    Run,
    Status,
    Trial,
)


# SQL-like metadata implementation, it could be SQLite, PostgreSQL, MySQL, etc.
class SQLStore(MetaStore):
    def __init__(self, db_url: str, init_tables: bool = False):
        self._engine = create_engine(db_url)
        self._session = sessionmaker(bind=self._engine)
        if init_tables:
            # create tables if not exist, will not affect existing tables.
            # Mostly used in tests.
            Base.metadata.create_all(self._engine)

    def create_project(
        self, name: str, description: str | None = None, meta: dict | None = None
    ) -> uuid.UUID:
        session = self._session()
        new_project = Project(
            name=name,
            description=description,
            meta=meta,
        )
        session.add(new_project)
        session.commit()
        project_id = new_project.uuid
        session.close()

        return project_id

    def get_project(self, project_id: uuid.UUID) -> Project | None:
        session = self._session()
        project = (
            session.query(Project)
            .filter(Project.uuid == project_id, Project.is_del == 0)
            .first()
        )
        session.close()
        return project

    def list_projects(self, page: int, page_size: int) -> list[Project]:
        session = self._session()
        projects = (
            session.query(Project)
            .filter(Project.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return projects

    def create_exp(
        self,
        name: str,
        project_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_exp = Experiment(
            name=name,
            project_id=project_id,
            description=description,
            meta=meta,
        )
        session.add(new_exp)
        session.commit()

        exp_id = new_exp.uuid
        session.close()

        return exp_id

    # Soft delete the experiment now. In the future, we may implement hard delete.
    def delete_exp(self, exp_id: uuid.UUID):
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == exp_id, Experiment.is_del == 0)
            .first()
        )
        if exp:
            exp.is_del = 1
            session.commit()
        session.close()

    # We don't support append-only update, the complete fields should be provided.
    def update_exp(self, exp_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == exp_id, Experiment.is_del == 0)
            .first()
        )
        if exp:
            for key, value in kwargs.items():
                setattr(exp, key, value)
            session.commit()
        session.close()

    # get_exp will ignore the deleted experiments.
    def get_exp(self, exp_id: uuid.UUID) -> Experiment | None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == exp_id, Experiment.is_del == 0)
            .first()
        )
        session.close()
        return exp

    def get_exp_by_name(self, name: str, project_id: uuid.UUID) -> Experiment | None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(
                Experiment.name == name,
                Experiment.project_id == project_id,
                Experiment.is_del == 0,
            )
            .first()
        )
        session.close()
        return exp

    # paginate the experiments in case of too many experiments.
    def list_exps(
        self, project_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[Experiment]:
        session = self._session()
        exps = (
            session.query(Experiment)
            .filter(Experiment.project_id == project_id, Experiment.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return exps

    def create_model(
        self,
        name: str,
        project_id: uuid.UUID,
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_model = Model(
            name=name,
            project_id=project_id,
            version=version,
            description=description,
            meta=meta,
        )
        session.add(new_model)
        session.commit()
        model_id = new_model.uuid
        session.close()

        return model_id

    def update_model(self, model_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        model = (
            session.query(Model)
            .filter(Model.uuid == model_id, Model.is_del == 0)
            .first()
        )
        if model:
            for key, value in kwargs.items():
                setattr(model, key, value)
            session.commit()
        session.close()

    def get_model(self, model_id: uuid.UUID) -> Model | None:
        session = self._session()
        model = (
            session.query(Model)
            .filter(Model.uuid == model_id, Model.is_del == 0)
            .first()
        )
        session.close()
        return model

    def list_models(self, page: int = 0, page_size: int = 10) -> list[Model]:
        session = self._session()
        models = (
            session.query(Model)
            .filter(Model.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return models

    def delete_model(self, model_id: uuid.UUID):
        session = self._session()
        model = (
            session.query(Model)
            .filter(Model.uuid == model_id, Model.is_del == 0)
            .first()
        )
        if model:
            model.is_del = 1
            session.commit()
        session.close()

    def create_trial(
        self,
        name: str,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        session = self._session()
        new_trial = Trial(
            project_id=project_id,
            experiment_id=experiment_id,
            name=name,
            description=description,
            meta=meta,
            params=params,
            status=status,
        )
        session.add(new_trial)
        session.commit()

        trial_id = new_trial.uuid
        session.close()

        return trial_id

    def get_trial(self, trial_id: uuid.UUID) -> Trial | None:
        session = self._session()
        trial = (
            session.query(Trial)
            .filter(Trial.uuid == trial_id, Trial.is_del == 0)
            .first()
        )
        session.close()
        return trial

    # TODO: should we use join to get the trial by experiment name?
    def get_trial_by_name(
        self, trial_name: str, experiment_id: uuid.UUID
    ) -> Trial | None:
        # make sure the experiment exists
        exp = self.get_exp(experiment_id)
        if exp is None:
            return None

        session = self._session()
        trial = (
            session.query(Trial)
            .filter(
                Trial.name == trial_name,
                Trial.experiment_id == experiment_id,
                Trial.is_del == 0,
            )
            .first()
        )
        session.close()
        return trial

    def list_trials_by_experiment_id(
        self, experiment_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[Trial]:
        session = self._session()
        trials = (
            session.query(Trial)
            .filter(Trial.experiment_id == experiment_id, Trial.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return trials

    def update_trial(self, trial_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        trial = (
            session.query(Trial)
            .filter(Trial.uuid == trial_id, Trial.is_del == 0)
            .first()
        )
        if trial:
            for key, value in kwargs.items():
                setattr(trial, key, value)
            session.commit()
        session.close()

    def create_run(
        self,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        trial_id: uuid.UUID,
        meta: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        session = self._session()
        new_run = Run(
            project_id=project_id,
            experiment_id=experiment_id,
            trial_id=trial_id,
            meta=meta,
            status=status,
        )
        session.add(new_run)
        session.commit()
        run_id = new_run.uuid
        session.close()

        return run_id

    def update_run(self, run_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        run = session.query(Run).filter(Run.uuid == run_id, Run.is_del == 0).first()
        if run:
            for key, value in kwargs.items():
                setattr(run, key, value)
            session.commit()
        session.close()

    def get_run(self, run_id: uuid.UUID) -> Run | None:
        session = self._session()
        run = session.query(Run).filter(Run.uuid == run_id, Run.is_del == 0).first()
        session.close()
        return run

    def list_runs_by_trial_id(
        self, trial_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[Run]:
        session = self._session()
        runs = (
            session.query(Run)
            .filter(Run.trial_id == trial_id, Run.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return runs

    def create_metric(
        self,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        trial_id: uuid.UUID,
        run_id: uuid.UUID,
        key: str,
        value: float,
        step: int,
    ) -> uuid.UUID:
        session = self._session()
        new_metric = Metric(
            project_id=project_id,
            experiment_id=experiment_id,
            trial_id=trial_id,
            run_id=run_id,
            key=key,
            value=value,
            step=step,
        )
        session.add(new_metric)
        session.commit()
        new_metric_id = new_metric.uuid
        session.close()
        return new_metric_id

    def list_metrics_by_trial_id(
        self, trial_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[Metric]:
        session = self._session()
        metrics = (
            session.query(Metric)
            .filter(Metric.trial_id == trial_id)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return metrics
