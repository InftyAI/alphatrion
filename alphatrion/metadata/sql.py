from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.metadata.base import MetaStore
from alphatrion.metadata.sql_models import Base, Experiment, Model


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
        labels: dict | None = None,
    ):
        session = self._session()
        new_exp = Experiment(
            name=name,
            description=description,
            project_id=project_id,
            meta=meta,
            labels=labels,
        )
        session.add(new_exp)
        session.commit()
        session.close()

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
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        session = self._session()
        new_model = Model(
            name=name,
            version=version,
            description=description,
            meta=meta,
            labels=labels,
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
