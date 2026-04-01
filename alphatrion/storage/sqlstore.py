import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion.storage.metastore import MetaStore
from alphatrion.storage.sql_models import (
    Agent,
    AgentSession,
    AgentType,
    Base,
    Dataset,
    Experiment,
    ExperimentLabel,
    ExperimentTag,
    MemberRole,
    Metric,
    Organization,
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

    # ---------- Organization APIs ----------

    def create_organization(
        self,
        name: str,
        uuid: uuid.UUID | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_org = Organization(
            name=name,
            description=description,
            meta=meta,
        )
        if uuid is not None:
            new_org.uuid = uuid

        session.add(new_org)
        session.commit()
        org_id = new_org.uuid
        session.close()

        return org_id

    def get_organization(self, org_id: uuid.UUID) -> Organization | None:
        session = self._session()
        org = (
            session.query(Organization)
            .filter(Organization.uuid == org_id, Organization.is_del == 0)
            .first()
        )
        session.close()
        return org

    def list_organizations(
        self, page: int = 0, page_size: int = 10
    ) -> list[Organization]:
        session = self._session()
        orgs = (
            session.query(Organization)
            .filter(Organization.is_del == 0)
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return orgs

    def update_organization(self, org_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        org = (
            session.query(Organization)
            .filter(Organization.uuid == org_id, Organization.is_del == 0)
            .first()
        )
        if org:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if org.meta is None:
                        org.meta = {}
                    org.meta.update(value)
                else:
                    setattr(org, key, value)
            session.commit()
        session.close()

    def delete_organization(self, org_id: uuid.UUID) -> bool:
        session = self._session()
        org = (
            session.query(Organization)
            .filter(Organization.uuid == org_id, Organization.is_del == 0)
            .first()
        )
        if org:
            org.is_del = 1
            session.commit()
            session.close()
            return True
        session.close()
        return False

    # ---------- Team APIs ----------

    # If uuid is provided, we will use the provided uuid for the new team.
    # This is useful for binding with external team management system where
    # the team id is already determined.
    def create_team(
        self,
        name: str,
        org_id: uuid.UUID,
        uuid: uuid.UUID | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_team = Team(
            org_id=org_id,
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
        user = self.get_user(user_id)

        # If user is admin, return all teams in the organization.
        if user and self.user_is_super_admin_in_org(user_id, user.org_id):
            teams = (
                session.query(Team)
                .filter(Team.org_id == user.org_id, Team.is_del == 0)
                .all()
            )
            session.close()
            return teams

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
        name: str,
        email: str,
        org_id: uuid.UUID,
        password_hash: str | None = None,
        uuid: uuid.UUID | None = None,
        avatar_url: str | None = None,
        team_id: uuid.UUID | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        # If no password_hash provided, use default (user must change on first login)
        if password_hash is None:
            from alphatrion.server.auth import hash_password

            password_hash = hash_password("changeme123")

        user = User(
            org_id=org_id,
            name=name,
            email=email,
            password_hash=password_hash,
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
                    org_id=org_id,
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

    def get_user_by_email(self, email: str) -> User | None:
        session = self._session()
        user = session.query(User).filter(User.email == email, User.is_del == 0).first()
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
        role: MemberRole = MemberRole.MEMBER,
    ) -> bool:
        """Add a user to a team"""
        session = self._session()

        # Validate user exists
        user = self.get_user(user_id)
        if not user:
            session.close()
            raise ValueError(f"User with id {user_id} not found")

        # Validate team exists
        team = self.get_team(team_id)
        if not team:
            session.close()
            raise ValueError(f"Team with id {team_id} not found")

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
            org_id=user.org_id,
            user_id=user_id,
            team_id=team_id,
            role=role,
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

    # ---------- Model APIs ----------

    # def create_model(
    #     self,
    #     name: str,
    #     team_id: uuid.UUID,
    #     version: str = "latest",
    #     description: str | None = None,
    #     meta: dict | None = None,
    # ) -> uuid.UUID:
    #     session = self._session()
    #     new_model = Model(
    #         name=name,
    #         team_id=team_id,
    #         version=version,
    #         description=description,
    #         meta=meta,
    #     )
    #     session.add(new_model)
    #     session.commit()
    #     model_id = new_model.uuid
    #     session.close()

    #     return model_id

    # def update_model(self, model_id: uuid.UUID, **kwargs) -> None:
    #     session = self._session()
    #     model = (
    #         session.query(Model)
    #         .filter(Model.uuid == model_id, Model.is_del == 0)
    #         .first()
    #     )
    #     if model:
    #         for key, value in kwargs.items():
    #             if key == "meta" and isinstance(value, dict):
    #                 if model.meta is None:
    #                     model.meta = {}
    #                 model.meta.update(value)
    #             else:
    #                 setattr(model, key, value)
    #         session.commit()
    #     session.close()

    # def get_model(self, model_id: uuid.UUID) -> Model | None:
    #     session = self._session()
    #     model = (
    #         session.query(Model)
    #         .filter(Model.uuid == model_id, Model.is_del == 0)
    #         .first()
    #     )
    #     session.close()
    #     return model

    # def list_models(self, page: int = 0, page_size: int = 10) -> list[Model]:
    #     session = self._session()
    #     models = (
    #         session.query(Model)
    #         .filter(Model.is_del == 0)
    #         .offset(page * page_size)
    #         .limit(page_size)
    #         .all()
    #     )
    #     session.close()
    #     return models

    # def delete_model(self, model_id: uuid.UUID):
    #     session = self._session()
    #     model = (
    #         session.query(Model)
    #         .filter(Model.uuid == model_id, Model.is_del == 0)
    #         .first()
    #     )
    #     if model:
    #         model.is_del = 1
    #         session.commit()
    #     session.close()

    # ---------- Experiment APIs ----------

    def create_experiment(
        self,
        name: str,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        description: str | None = None,
        labels: str | None = None,
        tags: list[str] | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        uid = uuid.uuid4()

        session = self._session()
        # TODO: add back the validation.
        # # verify user is in the team
        # membership = (
        #     session.query(TeamMember)
        #     .filter(
        #         TeamMember.user_id == user_id,
        #         TeamMember.team_id == team_id,
        #     )
        #     .first()
        # )
        # if membership is None:
        #     session.close()
        #     raise ValueError("User must be a member of the team to create experiment")

        new_exp = Experiment(
            uuid=uid,
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            name=name,
            description=description,
            meta=meta,
            params=params,
            status=status,
        )
        session.add(new_exp)

        if labels:
            # labels look like "label1:value1,label2:value2",
            label_pairs = labels.rstrip().split(",")
            for pair in label_pairs:
                if ":" in pair:
                    label_name, label_value = pair.split(":", 1)
                elif "=" in pair:
                    label_name, label_value = pair.split("=", 1)
                else:
                    continue  # skip invalid label

                exp_label = ExperimentLabel(
                    org_id=org_id,
                    team_id=team_id,
                    experiment_id=uid,
                    label_name=label_name.strip(),
                    label_value=label_value.strip(),
                )
                session.add(exp_label)

        if tags:
            for tag in [t.strip() for t in tags]:
                if tag:
                    exp_tag = ExperimentTag(
                        org_id=org_id,
                        team_id=team_id,
                        experiment_id=uid,
                        tag=tag,
                    )
                    session.add(exp_tag)

        session.commit()

        exp_id = new_exp.uuid
        assert exp_id == uid
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

    # Different team may have the same experiment name.
    def get_exp_by_name(
        self, name: str, team_id: uuid.UUID, include_deleted: bool = False
    ) -> Experiment | None:
        # make sure the team exists
        team = self.get_team(team_id)
        if team is None:
            return None

        session = self._session()
        query = session.query(Experiment).filter(
            Experiment.name == name,
            Experiment.team_id == team_id,
        )
        if not include_deleted:
            query = query.filter(Experiment.is_del == 0)
        trial = query.first()
        session.close()
        return trial

    def list_experiments(
        self,
        team_id: uuid.UUID,
        label_name: str | None = None,
        label_value: str | None = None,
        tag: str | None = None,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Experiment]:
        session = self._session()
        query = session.query(Experiment).filter(
            Experiment.team_id == team_id,
            Experiment.is_del == 0,
        )

        if label_name:
            query = query.join(
                ExperimentLabel, ExperimentLabel.experiment_id == Experiment.uuid
            ).filter(ExperimentLabel.label_name == label_name)
            if label_value is not None:
                query = query.filter(ExperimentLabel.label_value == label_value)

        if tag:
            query = query.join(
                ExperimentTag, ExperimentTag.experiment_id == Experiment.uuid
            ).filter(ExperimentTag.tag == tag)

        exps = (
            query.order_by(
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

    def list_labels_by_exp_id(self, experiment_id: uuid.UUID) -> list[ExperimentLabel]:
        session = self._session()
        labels = (
            session.query(ExperimentLabel)
            .filter(ExperimentLabel.experiment_id == experiment_id)
            .order_by(ExperimentLabel.created_at.asc())
            .all()
        )
        session.close()
        return labels

    def list_tags_by_exp_id(self, experiment_id: uuid.UUID) -> list[ExperimentTag]:
        session = self._session()
        tags = (
            session.query(ExperimentTag)
            .filter(ExperimentTag.experiment_id == experiment_id)
            .order_by(ExperimentTag.created_at.asc())
            .all()
        )
        session.close()
        return tags

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

    def delete_experiment(self, experiment_id: uuid.UUID) -> bool:
        session = self._session()

        # Try to delete the experiment
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == experiment_id, Experiment.is_del == 0)
            .first()
        )

        if exp and exp.status == Status.RUNNING:
            raise ValueError(
                "Cannot delete a running experiment. Please stop it first."
            )

        # Delete all runs associated with this experiment
        # (regardless of experiment status)
        session.query(Run).filter(Run.experiment_id == experiment_id).update(
            {Run.is_del: 1}, synchronize_session=False
        )
        if exp:
            exp.is_del = 1
            session.commit()
            session.close()
            return True

        # Even if experiment doesn't exist, commit the run deletions
        session.commit()
        session.close()
        return False

    def delete_experiments(self, experiment_ids: list[uuid.UUID]) -> int:
        """
        Batch delete experiments by setting is_del flag.
        Also deletes all associated runs.
        Returns the number of experiments successfully deleted.
        Caller must ensure user has permission to delete these experiments.
        """
        session = self._session()
        # Delete the experiments
        # if experiment is running, skip deletion for that experiment
        filtered_exps = (
            session.query(Experiment.uuid)
            .filter(
                Experiment.uuid.in_(experiment_ids),
                Experiment.is_del == 0,
                Experiment.status != Status.RUNNING,
            )
            .all()
        )
        filtered_exp_ids = [exp_id for (exp_id,) in filtered_exps]  # unpack tuples

        deleted_count = (
            session.query(Experiment)
            .filter(Experiment.uuid.in_(filtered_exp_ids))
            .update({Experiment.is_del: 1}, synchronize_session=False)
        )
        # Delete all runs associated with these experiments
        session.query(Run).filter(Run.experiment_id.in_(filtered_exp_ids)).update(
            {Run.is_del: 1}, synchronize_session=False
        )
        session.commit()
        session.close()
        return deleted_count

    # ---------- Agent APIs ----------

    def create_agent(
        self,
        name: str,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        type: AgentType = AgentType.CLAUDE,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        uid = uuid.uuid4()
        session = self._session()

        new_agent = Agent(
            uuid=uid,
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            name=name,
            type=type,
            description=description,
            meta=meta,
        )
        session.add(new_agent)
        session.commit()

        agent_id = new_agent.uuid
        assert agent_id == uid
        session.close()

        return agent_id

    def get_agent(self, agent_id: uuid.UUID) -> Agent | None:
        session = self._session()
        agent = (
            session.query(Agent)
            .filter(Agent.uuid == agent_id, Agent.is_del == 0)
            .first()
        )
        session.close()
        return agent

    def get_agent_by_name(
        self, name: str, team_id: uuid.UUID, include_deleted: bool = False
    ) -> Agent | None:
        session = self._session()
        query = session.query(Agent).filter(
            Agent.name == name,
            Agent.team_id == team_id,
        )
        if not include_deleted:
            query = query.filter(Agent.is_del == 0)

        agent = query.first()
        session.close()
        return agent

    def list_agents_by_team_id(
        self,
        team_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
    ) -> list[Agent]:
        session = self._session()
        agents = (
            session.query(Agent)
            .filter(Agent.team_id == team_id, Agent.is_del == 0)
            .order_by(Agent.created_at.desc())
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return agents

    def count_agents(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(Agent)
            .filter(Agent.team_id == team_id, Agent.is_del == 0)
            .count()
        )
        session.close()
        return count

    def count_sessions(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(AgentSession)
            .filter(AgentSession.team_id == team_id, AgentSession.is_del == 0)
            .count()
        )
        session.close()
        return count

    def get_agent_by_type(
        self,
        user_id: uuid.UUID,
        agent_type: AgentType,
    ) -> Agent | None:
        session = self._session()
        agent = (
            session.query(Agent)
            .filter(
                Agent.user_id == user_id,
                Agent.type == agent_type,
                Agent.is_del == 0,
            )
            .first()
        )
        session.close()
        return agent

    # ---------- Session APIs ----------

    def create_session(
        self,
        agent_id: uuid.UUID,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        meta: dict | None = None,
        status: Status = Status.PENDING,
    ) -> uuid.UUID:
        uid = uuid.uuid4()
        session = self._session()

        new_session = AgentSession(
            uuid=uid,
            org_id=org_id,
            agent_id=agent_id,
            team_id=team_id,
            user_id=user_id,
            meta=meta,
            status=status,
        )
        session.add(new_session)
        session.commit()

        session_id = new_session.uuid
        assert session_id == uid
        session.close()
        return session_id

    def get_session(self, session_id: uuid.UUID) -> AgentSession | None:
        session = self._session()
        result = (
            session.query(AgentSession)
            .filter(AgentSession.uuid == session_id, AgentSession.is_del == 0)
            .first()
        )
        session.close()
        return result

    def list_sessions_by_agent_id(
        self, agent_id: uuid.UUID, page: int = 0, page_size: int = 10
    ) -> list[AgentSession]:
        session = self._session()
        sessions = (
            session.query(AgentSession)
            .filter(AgentSession.agent_id == agent_id, AgentSession.is_del == 0)
            .order_by(AgentSession.created_at.desc())
            .limit(page_size)
            .offset(page * page_size)
            .all()
        )
        session.close()
        return sessions

    def update_session(
        self,
        session_id: uuid.UUID,
        **kwargs,
    ) -> None:
        session = self._session()
        db_session = (
            session.query(AgentSession).filter(AgentSession.uuid == session_id).first()
        )
        if db_session:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if db_session.meta is None:
                        db_session.meta = {}
                    db_session.meta.update(value)
                else:
                    setattr(db_session, key, value)
            session.commit()
        session.close()

    # ---------- Run APIs ----------

    def create_run(
        self,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        experiment_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        meta: dict | None = None,
        status: Status = Status.PENDING,
        duration: float | None = None,
        usage: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()

        new_run = Run(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            experiment_id=experiment_id,
            session_id=session_id,
            meta=meta,
            status=status,
            duration=duration,
            usage=usage,
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
        experiment_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        session = self._session()
        runs = (
            session.query(Run)
            .filter(Run.experiment_id == experiment_id, Run.is_del == 0)
            .order_by(
                getattr(Run, order_by).desc() if order_desc else getattr(Run, order_by)
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return runs

    def list_runs_by_session_id(
        self,
        session_id: uuid.UUID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        session = self._session()
        runs = (
            session.query(Run)
            .filter(Run.session_id == session_id, Run.is_del == 0)
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
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        experiment_id: uuid.UUID,
        run_id: uuid.UUID,
        key: str,
        value: float,
    ) -> uuid.UUID:
        session = self._session()
        new_metric = Metric(
            org_id=org_id,
            team_id=team_id,
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

    # ---------- Dataset APIs ----------

    def create_dataset(
        self,
        name: str,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        path: str,
        experiment_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> uuid.UUID:
        session = self._session()
        new_dataset = Dataset(
            org_id=org_id,
            name=name,
            team_id=team_id,
            user_id=user_id,
            path=path,
            description=description,
            meta=meta,
            experiment_id=experiment_id,
            run_id=run_id,
        )
        session.add(new_dataset)
        session.commit()
        dataset_id = new_dataset.uuid
        session.close()
        return dataset_id

    def get_dataset(self, dataset_id: uuid.UUID) -> Dataset | None:
        session = self._session()
        dataset = (
            session.query(Dataset)
            .filter(Dataset.uuid == dataset_id, Dataset.is_del == 0)
            .first()
        )
        session.close()
        return dataset

    def count_datasets(self, team_id: uuid.UUID) -> int:
        session = self._session()
        count = (
            session.query(Dataset)
            .filter(Dataset.team_id == team_id, Dataset.is_del == 0)
            .count()
        )
        session.close()
        return count

    def list_datasets(
        self,
        team_id: uuid.UUID,
        experiment_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        name: str | None = None,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Dataset]:
        session = self._session()
        query = session.query(Dataset).filter(
            Dataset.team_id == team_id, Dataset.is_del == 0
        )
        if experiment_id is not None:
            query = query.filter(Dataset.experiment_id == experiment_id)
        if run_id is not None:
            query = query.filter(Dataset.run_id == run_id)
        if name is not None:
            query = query.filter(Dataset.name == name)

        datasets = (
            query.order_by(
                getattr(Dataset, order_by).desc()
                if order_desc
                else getattr(Dataset, order_by)
            )
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        session.close()
        return datasets

    def update_dataset(self, dataset_id: uuid.UUID, **kwargs) -> None:
        session = self._session()
        dataset = (
            session.query(Dataset)
            .filter(Dataset.uuid == dataset_id, Dataset.is_del == 0)
            .first()
        )
        if dataset:
            for key, value in kwargs.items():
                if key == "meta" and isinstance(value, dict):
                    if dataset.meta is None:
                        dataset.meta = {}
                    dataset.meta.update(value)
                else:
                    setattr(dataset, key, value)
            session.commit()
        session.close()

    def delete_dataset(self, dataset_id: uuid.UUID) -> bool:
        session = self._session()
        dataset = (
            session.query(Dataset)
            .filter(Dataset.uuid == dataset_id, Dataset.is_del == 0)
            .first()
        )
        if dataset:
            dataset.is_del = 1
            session.commit()
            session.close()
            return True
        session.close()
        return False

    # ---------- Permission APIs ----------

    def user_is_super_admin_in_org(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        session = self._session()
        admin_membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.user_id == user_id,
                TeamMember.org_id == org_id,
                TeamMember.role == MemberRole.SUPER_ADMIN,
            )
            .first()
        )
        session.close()
        return admin_membership is not None

    def team_is_accessible_to_user(
        self, team_id: uuid.UUID, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        session = self._session()

        if self.user_is_super_admin_in_org(user_id, org_id):
            session.close()
            return True

        # Otherwise, check if user is a member of the specific team
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None

    def org_is_accessible_to_user(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        session = self._session()
        user = (
            session.query(User)
            .filter(User.uuid == user_id, User.org_id == org_id, User.is_del == 0)
            .first()
        )
        session.close()
        return user is not None

    def experiment_is_accessible_to_user(
        self, experiment_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        session = self._session()
        exp = (
            session.query(Experiment)
            .filter(Experiment.uuid == experiment_id, Experiment.is_del == 0)
            .first()
        )
        if exp is None:
            session.close()
            return False

        if self.user_is_super_admin_in_org(user_id, exp.org_id):
            session.close()
            return True

        # Check if user is in the team that the experiment belongs to
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == exp.team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None

    def run_is_accessible_to_user(self, run_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        session = self._session()
        run = session.query(Run).filter(Run.uuid == run_id, Run.is_del == 0).first()
        if run is None:
            session.close()
            return False

        if self.user_is_super_admin_in_org(user_id, run.org_id):
            session.close()
            return True

        # Check if user is in the team that the experiment belongs to
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == run.team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None

    def agent_is_accessible_to_user(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        session = self._session()
        agent = (
            session.query(Agent)
            .filter(Agent.uuid == agent_id, Agent.is_del == 0)
            .first()
        )
        if agent is None:
            session.close()
            return False

        if self.user_is_super_admin_in_org(user_id, agent.org_id):
            session.close()
            return True

        # Check if user is in the team that the agent belongs to
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == agent.team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None

    def session_is_accessible_to_user(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        session = self._session()
        agent_session = (
            session.query(AgentSession)
            .filter(AgentSession.uuid == session_id, AgentSession.is_del == 0)
            .first()
        )
        if agent_session is None:
            session.close()
            return False

        if self.user_is_super_admin_in_org(user_id, agent_session.org_id):
            session.close()
            return True

        # Check if user is in the team that the session belongs to
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == agent_session.team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None

    def dataset_is_accessible_to_user(
        self, dataset_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        session = self._session()
        dst = (
            session.query(Dataset)
            .filter(Dataset.uuid == dataset_id, Agent.is_del == 0)
            .first()
        )
        if dst is None:
            session.close()
            return False

        if self.user_is_super_admin_in_org(user_id, dst.org_id):
            session.close()
            return True

        # Check if user is in the team that the agent belongs to
        membership = (
            session.query(TeamMember)
            .filter(
                TeamMember.team_id == dst.team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        session.close()
        return membership is not None
