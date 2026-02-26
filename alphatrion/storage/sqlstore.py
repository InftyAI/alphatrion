import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.storage.metastore import MetaStore
from alphatrion.storage.sql_models import (
    Base,
    ContentSnapshot,
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

    # If uuid is provided, we will use the provided uuid for the new team.
    # This is useful for binding with external team management system where
    # the team id is already determined.
    def create_team(
        self,
        name: str,
        uuid: uuid.UUID | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_team = Team(
            name=name,
            description=description,
            meta=meta,
        )
        if uuid is not None:
            new_team.uuid = uuid

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

    # If uuid is provided, we will use the provided uuid for the new user.
    # This is useful for binding with external user management system where
    # the user id is already determined.
    def create_user(
        self,
        username: str,
        email: str,
        uuid: uuid.UUID | None = None,
        avatar_url: str | None = None,
        team_id: uuid.UUID | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        user = User(
            username=username,
            email=email,
            avatar_url=avatar_url,
            meta=meta,
        )
        if uuid is not None:
            user.uuid = uuid

        # If team_id is not provided, we will just create the user
        # without any team association.
        if team_id is None:
            session = self._session()
            session.add(user)
            session.commit()
            user_id = user.uuid
            session.close()

            return user_id
        else:
            # If team_id is provided, we will create the user and
            # add to the team in a transaction.
            session = self._session()
            try:
                session.add(user)
                session.flush()  # flush to get the new user's id

                new_member = TeamMember(
                    user_id=user.uuid,
                    team_id=team_id,
                )
                session.add(new_member)
                session.commit()
                user_id = user.uuid
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

    # Only for testing purpose now.
    def get_team_members_by_user_id(self, user_id: uuid.UUID) -> list[TeamMember]:
        """Get all team memberships for a user"""
        session = self._session()
        members = session.query(TeamMember).filter(TeamMember.user_id == user_id).all()
        session.close()
        return members

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

    def get_experiment_by_name(
        self, name: str, project_id: uuid.UUID
    ) -> Experiment | None:
        """Alias for get_exp_by_name."""
        return self.get_exp_by_name(name, project_id)

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
        if page_size == -1:
            runs = (
                session.query(Run)
                .filter(Run.experiment_id == exp_id, Run.is_del == 0)
                .order_by(
                    getattr(Run, order_by).desc() if order_desc else getattr(Run, order_by)
                )
                .all()
            )
        else:
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

    def list_metrics_by_experiment_id_and_key(
        self,
        experiment_id: uuid.UUID,
        key: str,
    ) -> list[Metric]:
        """Get metrics for a specific key in an experiment."""
        session = self._session()
        metrics = (
            session.query(Metric)
            .filter(Metric.experiment_id == experiment_id, Metric.key == key)
            .order_by(Metric.created_at.asc())
            .all()
        )
        session.close()
        return metrics


    def list_metrics_by_run_id(self, run_id: uuid.UUID) -> list[Metric]:
        session = self._session()
        metrics = (
            session.query(Metric)
            .filter(Metric.run_id == run_id)
            .order_by(Metric.created_at.asc())
            .all()
        )
        session.close()
        return metrics

    def list_metric_keys_by_experiment_id(self, experiment_id: uuid.UUID) -> list[str]:
        """Get unique metric keys for an experiment."""
        session = self._session()
        keys = (
            session.query(Metric.key)
            .filter(Metric.experiment_id == experiment_id)
            .distinct()
            .all()
        )
        session.close()
        return [k[0] for k in keys]

    # ---------- ContentSnapshot APIs ----------

    def create_content_snapshot(
        self,
        team_id: uuid.UUID,
        project_id: uuid.UUID,
        experiment_id: uuid.UUID,
        content_uid: str,
        content_text: str,
        run_id: uuid.UUID | None = None,
        parent_uid: str | None = None,
        co_parent_uids: list[str] | None = None,
        fitness: dict | list | float | None = None,
        evaluation: dict | None = None,
        metainfo: dict | None = None,
        language: str = "python",
    ) -> uuid.UUID:
        """Create a content snapshot."""
        session = self._session()
        new_snapshot = ContentSnapshot(
            team_id=team_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_id=run_id,
            content_uid=content_uid,
            content_text=content_text,
            parent_uid=parent_uid,
            co_parent_uids=co_parent_uids,
            fitness=fitness,
            evaluation=evaluation,
            metainfo=metainfo,
            language=language,
        )
        session.add(new_snapshot)
        session.commit()
        snapshot_id = new_snapshot.uuid
        session.close()
        return snapshot_id

    def get_content_snapshot(self, snapshot_id: uuid.UUID) -> ContentSnapshot | None:
        """Get a content snapshot by ID."""
        session = self._session()
        snapshot = (
            session.query(ContentSnapshot)
            .filter(ContentSnapshot.uuid == snapshot_id, ContentSnapshot.is_del == 0)
            .first()
        )
        session.close()
        return snapshot

    def list_content_snapshots_by_experiment_id(
        self,
        experiment_id: uuid.UUID,
        page: int = 0,
        page_size: int = 100,
    ) -> list[ContentSnapshot]:
        """List content snapshots for an experiment."""
        session = self._session()
        snapshots = (
            session.query(ContentSnapshot)
            .filter(
                ContentSnapshot.experiment_id == experiment_id,
                ContentSnapshot.is_del == 0,
            )
            .order_by(ContentSnapshot.created_at.desc())
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return snapshots

    def list_content_snapshots_summary_by_experiment_id(
        self,
        experiment_id: uuid.UUID,
        page: int = 0,
        page_size: int = 100,
    ) -> list[dict]:
        """List content snapshot summaries (without full text) for an experiment."""
        session = self._session()
        # Query specific columns to avoid loading content_text
        snapshots = (
            session.query(
                ContentSnapshot.uuid,
                ContentSnapshot.team_id,
                ContentSnapshot.project_id,
                ContentSnapshot.experiment_id,
                ContentSnapshot.run_id,
                ContentSnapshot.content_uid,
                ContentSnapshot.parent_uid,
                ContentSnapshot.co_parent_uids,
                ContentSnapshot.fitness,
                ContentSnapshot.evaluation,
                ContentSnapshot.metainfo,
                ContentSnapshot.language,
                ContentSnapshot.created_at,
            )
            .filter(
                ContentSnapshot.experiment_id == experiment_id,
                ContentSnapshot.is_del == 0,
            )
            .order_by(ContentSnapshot.created_at.desc())
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()

        # Convert to dict format
        return [
            {
                "id": str(s.uuid),
                "team_id": str(s.team_id),
                "project_id": str(s.project_id),
                "experiment_id": str(s.experiment_id),
                "run_id": str(s.run_id) if s.run_id else None,
                "content_uid": s.content_uid,
                "parent_uid": s.parent_uid,
                "co_parent_uids": s.co_parent_uids,
                "fitness": s.fitness,
                "evaluation": s.evaluation,
                "metainfo": s.metainfo,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
            }
            for s in snapshots
        ]

    def get_content_snapshot_by_content_uid(
        self, content_uid: str, experiment_id: uuid.UUID
    ) -> ContentSnapshot | None:
        """Get a content snapshot by content UID."""
        session = self._session()
        snapshot = (
            session.query(ContentSnapshot)
            .filter(
                ContentSnapshot.content_uid == content_uid,
                ContentSnapshot.experiment_id == experiment_id,
                ContentSnapshot.is_del == 0,
            )
            .first()
        )
        session.close()
        return snapshot
