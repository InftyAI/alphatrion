#!/usr/bin/env python3

import os
import random
import sys
import uuid
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion import consts
from alphatrion.metadata.sql_models import (
    Base,
    Experiment,
    Metric,
    Project,
    Run,
    Status,
    Team,
    User,
)

load_dotenv()

DATABASE_URL = os.getenv(consts.METADATA_DB_URL)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

fake = Faker()


def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


def generate_team() -> Team:
    return Team(
        uuid=uuid.uuid4(),
        name=fake.bs().title(),
        description=fake.catch_phrase(),
        meta=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
    )


def generate_user(teams: list[Team]) -> User:
    return User(
        uuid=uuid.uuid4(),
        username=fake.user_name(),
        email=fake.email(),
        team_id=random.choice(teams).uuid,
        meta=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
    )


def generate_project(users: list[User]) -> Project:
    user = random.choice(users)
    team = (
        session.query(Team).filter(Team.uuid == user.team_id, Team.is_del == 0).first()
    )
    return Project(
        name=fake.bs().title(),
        description=fake.catch_phrase(),
        meta=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
        creator_id=user.uuid,
        team_id=team.uuid,
    )


def generate_experiment(projects: list[Project]) -> Experiment:
    proj = random.choice(projects)
    user_id = proj.creator_id
    return Experiment(
        team_id=proj.team_id,
        user_id=user_id,
        project_id=proj.uuid,
        name=fake.bs().title(),
        description=fake.catch_phrase(),
        meta=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
        params=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
        duration=random.uniform(0.1, 1000.0),
        status=random.choice(list(Status)).value,
    )


def generate_run(exps: list[Experiment]) -> Run:
    exp = random.choice(exps)
    user_id = exp.user_id
    return Run(
        team_id=exp.team_id,
        user_id=user_id,
        project_id=exp.project_id,
        experiment_id=exp.uuid,
        meta=make_json_serializable(
            fake.pydict(nb_elements=2, variable_nb_elements=True)
        ),
        status=random.choice(list(Status)).value,
    )


def generate_metric(runs: list[Run]) -> Metric:
    run = random.choice(runs)
    return Metric(
        team_id=run.team_id,
        project_id=run.project_id,
        experiment_id=run.experiment_id,
        run_id=run.uuid,
        key=random.choice(["accuracy", "loss", "precision", "fitness"]),
        value=random.uniform(0, 1),
    )


def seed_all(
    num_teams: int,
    num_users: int,
    num_projs_per_team: int,
    num_exps_per_proj: int,
    num_runs_per_exp: int,
    num_metrics_per_run: int,
):
    Base.metadata.create_all(bind=engine)

    print("🌱 generating seeds ...")

    teams = [generate_team() for _ in range(num_teams)]
    session.add_all(teams)
    session.commit()

    users = [generate_user(teams) for _ in range(num_users)]
    session.add_all(users)
    session.commit()

    projs = [
        generate_project(users)
        for _ in range(num_projs_per_team)
        for _ in range(len(teams))
    ]
    session.add_all(projs)
    session.commit()

    exps = [
        generate_experiment(projs)
        for _ in range(num_exps_per_proj)
        for _ in range(len(projs))
    ]
    session.add_all(exps)
    session.commit()

    runs = [
        generate_run(exps) for _ in range(num_runs_per_exp) for _ in range(len(exps))
    ]
    session.add_all(runs)
    session.commit()

    metrics = [
        generate_metric(runs)
        for _ in range(num_metrics_per_run)
        for _ in range(len(runs))
    ]
    session.add_all(metrics)
    session.commit()

    print("🌳 seeding completed.")


def cleanup():
    print("🧹 cleaning up seeded data ...")
    session.query(Metric).delete()
    session.query(Run).delete()
    session.query(Team).delete()
    session.query(Experiment).delete()
    session.query(Project).delete()
    session.commit()
    print("🧼 cleanup completed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python script.py [cleanup|seed]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "cleanup":
        cleanup()
    elif action == "seed":
        seed_all(
            num_teams=3,
            num_users=15,
            num_projs_per_team=10,
            num_exps_per_proj=10,
            num_runs_per_exp=20,
            num_metrics_per_run=30,
        )
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
