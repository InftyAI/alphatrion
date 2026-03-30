# ruff: noqa: E501

#!/usr/bin/env python3

import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alphatrion import envs
from alphatrion.storage.sql_models import (
    Base,
    Experiment,
    Metric,
    Run,
    Status,
    Team,
    TeamMember,
    User,
)

load_dotenv()

DATABASE_URL = os.getenv(envs.METADATA_DB_URL)

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


def generate_user() -> User:
    return User(
        uuid=uuid.uuid4(),
        name=fake.user_name(),
        email=fake.email(),
        meta=make_json_serializable(
            fake.pydict(nb_elements=3, variable_nb_elements=True)
        ),
    )


def generate_team_user(teams: list[Team], user: User) -> TeamMember:
    team = random.choice(teams)
    return TeamMember(
        team_id=team.uuid,
        user_id=user.uuid,
    )


def generate_experiment(team_members: list[TeamMember]) -> Experiment:
    tm = random.choice(team_members)
    return Experiment(
        team_id=tm.team_id,
        user_id=tm.user_id,
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


def generate_run(exps: list[Experiment], created_at: datetime) -> Run:
    exp = random.choice(exps)
    user_id = exp.user_id
    run = Run(
        team_id=exp.team_id,
        user_id=user_id,
        experiment_id=exp.uuid,
        meta=make_json_serializable(
            fake.pydict(nb_elements=2, variable_nb_elements=True)
        ),
        # sample a status for the run, with a bias towards RUNNING and COMPLETED
        status=random.choices(
            population=[
                Status.PENDING,
                Status.RUNNING,
                Status.COMPLETED,
                Status.FAILED,
            ],
            weights=[0.1, 0.2, 0.6, 0.1],
            k=1,
        )[0].value,
        created_at=created_at,
    )
    return run


def generate_metric(name: str, run: Run, created_at: datetime) -> Metric:
    return Metric(
        team_id=run.team_id,
        experiment_id=run.experiment_id,
        run_id=run.uuid,
        key=name,
        value=random.uniform(0, 1),
        created_at=created_at,
    )


def seed_all(
    num_teams: int,
    num_users: int,
    num_exps_per_team: int,
    num_runs_per_exp: int,
    metrics: list[str],
):
    Base.metadata.create_all(bind=engine)

    print("🌱 generating seeds ...")

    teams = [generate_team() for _ in range(num_teams)]
    session.add_all(teams)
    session.commit()
    teams = session.query(Team).all()  # Refresh teams with IDs from DB

    users = [generate_user() for _ in range(num_users)]
    session.add_all(users)
    session.commit()
    users = session.query(User).all()  # Refresh users with IDs from DB

    members = [generate_team_user(teams, user) for user in users]
    session.add_all(members)
    session.commit()

    exps = [
        generate_experiment(members)
        for _ in range(num_exps_per_team)
        for _ in range(len(teams))
    ]
    session.add_all(exps)
    session.commit()
    exps = session.query(Experiment).all()  # Refresh experiments with IDs from DB

    generate_time = datetime.now()
    for _ in range(len(exps)):
        for _ in range(num_runs_per_exp):
            generate_time = generate_time + timedelta(
                minutes=5
            )  # Ensure different timestamps for each run
            run = generate_run(exps, generate_time)
            session.add(run)
            session.commit()

            for metric_key in metrics:
                generate_time = generate_time + timedelta(
                    minutes=3
                )  # Ensure different timestamps for each metric
                metric = generate_metric(metric_key, run, generate_time)
                session.add(metric)
                session.commit()

                print(
                    f"Generate metric {metric_key} for run {run.uuid} of experiment {run.experiment_id}, team {run.team_id} ..."
                )

    print("🌳 seeding completed.")


def cleanup():
    print("🧹 cleaning up seeded data ...")
    session.query(Metric).delete()
    session.query(Run).delete()
    session.query(Team).delete()
    session.query(Experiment).delete()
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
            num_teams=2,
            num_users=8,
            num_exps_per_team=10,
            num_runs_per_exp=100,
            metrics=["accuracy", "loss", "fitness"],
        )
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
