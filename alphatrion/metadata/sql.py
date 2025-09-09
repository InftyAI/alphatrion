from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.metadata.sql_models import Base, Experiment
from alphatrion.metadata.base import Metadata


# SQL-like metadata implementation, it could be SQLite, PostgreSQL, MySQL, etc.
class SQLMetadata(Metadata):
    def __init__(self, db_url: str, init_tables: bool = False):
        super().__init__()

        self._engine = create_engine(db_url)
        self._session = sessionmaker(bind=self._engine)
        if init_tables:
            # create tables if not exist, will not affect existing tables.
            # In production, use migrations instead.
            Base.metadata.create_all(self._engine)


    def create_exp(self, name: str, project_id: str, description: str | None, meta: dict | None):
        session = self._session()
        new_exp = Experiment(name=name, description=description, project_id=project_id, meta=meta)
        session.add(new_exp)
        session.commit()
        session.close()

    # Soft delete the experiment now. In the future, we may implement hard delete.
    def delete_exp(self, exp_id: int):
        session = self._session()
        exp = session.query(Experiment).filter(Experiment.id == exp_id).first()
        if exp and exp.is_del == 0:
            exp.is_del = 1
            session.commit()
        session.close()

    def update_exp(self, exp_id: int, **kwargs):
        session = self._session()
        exp = session.query(Experiment).filter(Experiment.id == exp_id).first()
        if exp:
            for key, value in kwargs.items():
                setattr(exp, key, value)
            session.commit()
        session.close()

    # get_exp will ignore the deleted experiments.
    def get_exp(self, exp_id: int) -> Experiment | None:
        session = self._session()
        exp = session.query(Experiment).filter(Experiment.id == exp_id, Experiment.is_del == 0).first()
        session.close()
        return exp

    # paginate the experiments in case of too many experiments.
    def list_exps(self, project_id: str, page: int, page_size: int) -> list[Experiment]:
        session = self._session()
        exps = session.query(Experiment).filter(Experiment.project_id == project_id).offset(page * page_size).limit(page_size).all()
        session.close()
        return exps
