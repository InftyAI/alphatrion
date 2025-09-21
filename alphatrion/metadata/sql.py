from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.metadata.base import MetaStore
from alphatrion.metadata.sql_models import (
    Base,
    Experiment,
    Metrics,
    Model,
    Trial,
    TrialStatus,
)


# SQL-like metadata implementation, it could be SQLite, PostgreSQL, MySQL, etc.
class SQLStore(MetaStore):
    def __init__(self, db_url: str, init_tables: bool = False):
        self._engine = create_engine(db_url)
        self._session = sessionmaker(bind=self._engine)
        if init_tables:
            # create tables if not exist, will not affect existing tables.
            # In production, use migrations instead.
            Base.metadata.create_all(self._engine)

    def create_exp(
        self,
        name: str,
        project_id: str,
        description: str | None,
        meta: dict | None,
    ) -> int:
        session = self._session()
        new_exp = Experiment(
            name=name,
            project_id=project_id,
            description=description,
            meta=meta,
        )
        session.add(new_exp)
        session.commit()

        exp_id = new_exp.id
        session.close()

        return exp_id

    # Soft delete the experiment now. In the future, we may implement hard delete.
    def delete_exp(self, exp_id: int):
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.id == exp_id, Experiment.is_del == 0)
            .first()
        )
        if exp:
            exp.is_del = 1
            session.commit()
        session.close()

    # We don't support append-only update, the complete fields should be provided.
    def update_exp(self, exp_id: int, **kwargs):
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.id == exp_id, Experiment.is_del == 0)
            .first()
        )
        if exp:
            for key, value in kwargs.items():
                setattr(exp, key, value)
            session.commit()
        session.close()

    # get_exp will ignore the deleted experiments.
    def get_exp(self, exp_id: int) -> Experiment | None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.id == exp_id, Experiment.is_del == 0)
            .first()
        )
        session.close()
        return exp

    # paginate the experiments in case of too many experiments.
    def list_exps(self, project_id: str, page: int, page_size: int) -> list[Experiment]:
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
        project_id: str,
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
    ):
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
        session.close()

    def update_model(self, model_id: int, **kwargs):
        session = self._session()
        model = (
            session.query(Model).filter(Model.id == model_id, Model.is_del == 0).first()
        )
        if model:
            for key, value in kwargs.items():
                setattr(model, key, value)
            session.commit()
        session.close()

    def get_model(self, model_id: int) -> Model | None:
        session = self._session()
        model = (
            session.query(Model).filter(Model.id == model_id, Model.is_del == 0).first()
        )
        session.close()
        return model

    def list_models(self, page: int, page_size: int) -> list[Model]:
        session = self._session()
        models = session.query(Model).offset(page * page_size).limit(page_size).all()
        session.close()
        return models

    def delete_model(self, model_id: int):
        session = self._session()
        model = (
            session.query(Model).filter(Model.id == model_id, Model.is_del == 0).first()
        )
        if model:
            model.is_del = 1
            session.commit()
        session.close()

    def create_trial(
        self,
        exp_id: int,
        description: str | None,
        meta: dict | None,
        params: dict | None = None,
        status: TrialStatus = TrialStatus.PENDING,
    ) -> int:
        session = self._session()
        new_trial = Trial(
            experiment_id=exp_id,
            description=description,
            meta=meta,
            params=params,
            status=status,
        )
        session.add(new_trial)
        session.commit()

        trial_id = new_trial.id
        session.close()

        return trial_id

    def get_trial(self, trial_id: int) -> Trial | None:
        session = self._session()
        trial = session.query(Trial).filter(Trial.id == trial_id).first()
        session.close()
        return trial

    def update_trial(self, trial_id: int, **kwargs):
        session = self._session()
        trial = session.query(Trial).filter(Trial.id == trial_id).first()
        if trial:
            for key, value in kwargs.items():
                setattr(trial, key, value)
            session.commit()
        session.close()

    def create_metric(self, trial_id: int, key: str, value: float, step: int):
        session = self._session()
        new_metric = Metrics(
            trial_id=trial_id,
            key=key,
            value=value,
            step=step,
        )
        session.add(new_metric)
        session.commit()
        session.close()

    def list_metrics(self, trial_id: int) -> list[Metrics]:
        session = self._session()
        metrics = session.query(Metrics).filter(Metrics.trial_id == trial_id).all()
        session.close()
        return metrics
