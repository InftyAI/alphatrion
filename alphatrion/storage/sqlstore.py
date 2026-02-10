import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.storage.metastore import MetaStore
from alphatrion.storage.sql_models import (
    Base,
    Experiment,
    Metric,
    Model,
    Project,
    Run,
    Status,
    Team,
    TeamMember,
    User,
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

    # ---------- Team APIs ----------

    def create_team(
        self, name: str, description: str | None = None, meta: dict | None = None
    ) -> uuid.UUID:
        session = self._session()
        new_team = Team(
            name=name,
            description=description,
            meta=meta,
        )
        session.add(new_team)
        session.commit()
        team_id = new_team.uuid
        session.close()

        return team_id

    def get_team(self, team_id: uuid.UUID) -> Team | None:
        session = self._session()
        team = (
            session.query(Team).filter(Team.uuid == team_id, Team.is_del == 0).first()
        )
        session.close()
        return team

    def list_user_teams(self, user_id: uuid.UUID) -> list[Team]:
        session = self._session()
        teams = (
            session.query(Team)
            .join(TeamMember, TeamMember.team_id == Team.uuid)
            .filter(
                TeamMember.user_id == user_id,
                Team.is_del == 0,
            )
            .all()
        )
        session.close()
        return teams

    # ---------- User APIs ----------

    def create_user(
        self,
        username: str,
        email: str,
        avatar_url: str | None = None,
        team_id: uuid.UUID | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        # If team_id is not provided, we will just create the user
        # without any team association.
        if team_id is None:
            session = self._session()
            new_user = User(
                username=username,
                email=email,
                avatar_url=avatar_url,
                meta=meta,
            )
            session.add(new_user)
            session.commit()
            user_id = new_user.uuid
            session.close()

            return user_id
        else:
            # If team_id is provided, we will create the user and
            # add to the team in a transaction.
            session = self._session()
            try:
                new_user = User(
                    username=username,
                    email=email,
                    avatar_url=avatar_url,
                    meta=meta,
                )
                session.add(new_user)
                session.flush()  # flush to get the new user's id

                new_member = TeamMember(
                    user_id=new_user.uuid,
                    team_id=team_id,
                )
                session.add(new_member)

                session.commit()
                user_id = new_user.uuid
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()

            return user_id

    def get_user(self, user_id: uuid.UUID) -> User | None:
        session = self._session()
        user = (
            session.query(User).filter(User.uuid == user_id, User.is_del == 0).first()
        )
        session.close()
        return user

    def update_user(self, user_id: uuid.UUID, **kwargs) -> User | None:
        session = self._session()
        user = (
            session.query(User).filter(User.uuid == user_id, User.is_del == 0).first()
        )
        if user:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if user.meta is None:
                        user.meta = {}
                    user.meta.update(value)
                else:
                    setattr(user, key, value)
            session.commit()
        session.close()

        return self.get_user(user_id)

    def list_users(
        self, team_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[User]:
        """List users in a team"""
        session = self._session()
        # Join TeamMember to get users in the team
        users = (
            session.query(User)
            .join(TeamMember, TeamMember.user_id == User.uuid)
            .filter(
                TeamMember.team_id == team_id,
                User.is_del == 0,
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return users

    # ---------- Team Member APIs ----------

    def add_user_to_team(
        self,
        user_id: uuid.UUID,
        team_id: uuid.UUID,
    ) -> bool:
        """Add a user to a team"""
        session = self._session()
        # Check if membership already exists
        existing = (
            session.query(TeamMember)
            .filter(
                TeamMember.user_id == user_id,
                TeamMember.team_id == team_id,
            )
            .first()
        )
        if existing:
            session.close()
            return False

        new_member = TeamMember(
            user_id=user_id,
            team_id=team_id,
        )
        session.add(new_member)
        session.commit()
        session.close()
        return True

    def remove_user_from_team(self, user_id: uuid.UUID, team_id: uuid.UUID) -> bool:
        """Remove a user from a team (hard delete)"""
        session = self._session()
        member = (
            session.query(TeamMember)
            .filter(
                TeamMember.user_id == user_id,
                TeamMember.team_id == team_id,
            )
            .first()
        )
        if member:
            session.delete(member)
            session.commit()
            session.close()
            return True
        session.close()
        return False

    def list_team_members(
        self, team_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[TeamMember]:
        """List all team members (memberships) for a team"""
        session = self._session()
        members = (
            session.query(TeamMember)
            .filter(TeamMember.team_id == team_id)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return members

    # ---------- Project APIs ----------

    def create_project(
        self,
        name: str,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_proj = Project(
            name=name,
            team_id=team_id,
            creator_id=user_id,
            description=description,
            meta=meta,
        )
        session.add(new_proj)
        session.commit()

        exp_id = new_proj.uuid
        session.close()

        return exp_id

    # Soft delete the project now.
    def delete_project(self, project_id: uuid.UUID):
        session = self._session()
        proj = (
            session.query(Project)
            .filter(Project.uuid == project_id, Project.is_del == 0)
            .first()
        )
        if proj:
            proj.is_del = 1
            session.commit()
        session.close()

    # We don't support append-only update, the complete fields should be provided.
    def update_project(self, project_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        proj = (
            session.query(Project)
            .filter(Project.uuid == project_id, Project.is_del == 0)
            .first()
        )
        if proj:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if proj.meta is None:
                        proj.meta = {}
                    proj.meta.update(value)
                else:
                    setattr(proj, key, value)
            session.commit()
        session.close()

    # get function will ignore the deleted ones.
    def get_project(self, project_id: uuid.UUID) -> Project | None:
        session = self._session()
        proj = (
            session.query(Project)
            .filter(Project.uuid == project_id, Project.is_del == 0)
            .first()
        )
        session.close()
        return proj

    def get_proj_by_name(self, name: str, team_id: uuid.UUID) -> Project | None:
        session = self._session()
        proj = (
            session.query(Project)
            .filter(
                Project.name == name,
                Project.team_id == team_id,
                Project.is_del == 0,
            )
            .first()
        )
        session.close()
        return proj

    # paginate the projects in case of too many projects.
    def list_projects(
        self,
        team_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Project]:
        session = self._session()
        projects = (
            session.query(Project)
            .filter(Project.team_id == team_id, Project.is_del == 0)
            .order_by(
                getattr(Project, order_by).desc()
                if order_desc
                else getattr(Project, order_by)
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return projects

    def count_projects(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(Project)
            .filter(Project.team_id == team_id, Project.is_del == 0)
            .count()
        )
        session.close()
        return count

    # ---------- Model APIs ----------

    def create_model(
        self,
        name: str,
        team_id: uuid.UUID,
        version: str = "latest",
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_model = Model(
            name=name,
            team_id=team_id,
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
                if key == "meta" and isinstance(value, dict):
                    if model.meta is None:
                        model.meta = {}
                    model.meta.update(value)
                else:
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

    # ---------- Experiment APIs ----------

    def create_experiment(
        self,
        name: str,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        session = self._session()
        new_exp = Experiment(
            team_id=team_id,
            user_id=user_id,
            project_id=project_id,
            name=name,
            description=description,
            meta=meta,
            params=params,
            status=status,
        )
        session.add(new_exp)
        session.commit()

        exp_id = new_exp.uuid
        session.close()

        return exp_id

    def get_experiment(self, experiment_id: uuid.UUID) -> Experiment | None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == experiment_id, Experiment.is_del == 0)
            .first()
        )
        session.close()
        return exp

    # Different project may have the same experiment name.
    def get_exp_by_name(self, name: str, project_id: uuid.UUID) -> Experiment | None:
        # make sure the project exists
        proj = self.get_project(project_id)
        if proj is None:
            return None

        session = self._session()
        trial = (
            session.query(Experiment)
            .filter(
                Experiment.name == name,
                Experiment.project_id == project_id,
                Experiment.is_del == 0,
            )
            .first()
        )
        session.close()
        return trial

    def list_exps_by_project_id(
        self,
        project_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Experiment]:
        session = self._session()
        exps = (
            session.query(Experiment)
            .filter(Experiment.project_id == project_id, Experiment.is_del == 0)
            .order_by(
                getattr(Experiment, order_by).desc()
                if order_desc
                else getattr(Experiment, order_by)
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return exps

    def update_experiment(self, experiment_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == experiment_id, Experiment.is_del == 0)
            .first()
        )
        if exp:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if exp.meta is None:
                        exp.meta = {}
                    exp.meta.update(value)
                else:
                    setattr(exp, key, value)
            session.commit()
        session.close()

    def count_experiments(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(Experiment)
            .filter(Experiment.team_id == team_id, Experiment.is_del == 0)
            .count()
        )
        session.close()
        return count

    def list_exps_by_timeframe(
        self, team_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> list[Experiment]:
        session = self._session()
        exps = (
            session.query(Experiment)
            .filter(
                Experiment.team_id == team_id,
                Experiment.created_at >= start_time,
                Experiment.created_at <= end_time,
                Experiment.is_del == 0,
            )
            .order_by(Experiment.created_at.asc())
            .all()
        )
        session.close()
        return exps

    # ---------- Run APIs ----------

    def create_run(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        meta: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        session = self._session()

        new_run = Run(
            project_id=project_id,
            team_id=team_id,
            user_id=user_id,
            experiment_id=experiment_id,
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
                if key == "meta" and isinstance(value, dict):
                    if run.meta is None:
                        run.meta = {}
                    run.meta.update(value)
                else:
                    setattr(run, key, value)
            session.commit()
        session.close()

    def get_run(self, run_id: uuid.UUID) -> Run | None:
        session = self._session()
        run = session.query(Run).filter(Run.uuid == run_id, Run.is_del == 0).first()
        session.close()
        return run

    def list_runs_by_exp_id(
        self,
        exp_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        session = self._session()
        runs = (
            session.query(Run)
            .filter(Run.experiment_id == exp_id, Run.is_del == 0)
            .order_by(
                getattr(Run, order_by).desc() if order_desc else getattr(Run, order_by)
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return runs

    def count_runs(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(Run).filter(Run.team_id == team_id, Run.is_del == 0).count()
        )
        session.close()
        return count

    # ---------- Metric APIs ----------

    def create_metric(
        self,
        team_id: uuid.UUID,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        run_id: uuid.UUID,
        key: str,
        value: float,
    ) -> uuid.UUID:
        session = self._session()
        new_metric = Metric(
            team_id=team_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_id=run_id,
            key=key,
            value=value,
        )
        session.add(new_metric)
        session.commit()
        new_metric_id = new_metric.uuid
        session.close()
        return new_metric_id

    def list_metrics_by_experiment_id(self, experiment_id: uuid.UUID) -> list[Metric]:
        session = self._session()
        metrics = (
            session.query(Metric)
            .filter(Metric.experiment_id == experiment_id)
            .order_by(Metric.created_at.asc())
            .all()
        )
        session.close()
        return metrics
