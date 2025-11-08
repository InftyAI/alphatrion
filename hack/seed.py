#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from curses import meta
import os
import uuid
import random
from decimal import Decimal

from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

from alphatrion.metadata.sql_models import Metric, Project, Experiment, Run, Trial, TrialStatus, Base
from alphatrion import consts

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

def generate_project() -> Project:
    return Project(
        uuid=uuid.uuid4(),
        name=fake.bs().title(),
        description=fake.catch_phrase(),
    )

def generate_experiment(projects: list[Project]) -> Experiment:
    return Experiment(
        name=fake.bs().title(),
        description=fake.catch_phrase(),
        meta=make_json_serializable(fake.pydict(nb_elements=3, variable_nb_elements=True)),
        project_id=random.choice(projects).uuid,
    )

def generate_trial(exps: list[Experiment]) -> Trial:
    exp = random.choice(exps)
    return Trial(
        project_id=exp.project_id,
        experiment_id=exp.uuid,
        name=fake.bs().title(),
        description=fake.catch_phrase(),
        meta=make_json_serializable(fake.pydict(nb_elements=3, variable_nb_elements=True)),
        params=make_json_serializable(fake.pydict(nb_elements=3, variable_nb_elements=True)),
        status=random.choice(list(TrialStatus)),
    )

def generate_run(trials: list[Trial]) -> Run:
    trial = random.choice(trials)
    return Run(
        project_id=trial.project_id,
        trial_id=trial.uuid,
    )

def generate_metric(runs: list[Run]) -> Metric:
    run = random.choice(runs)
    return Metric(
        project_id=run.project_id,
        trial_id=run.trial_id,
        key=random.choice(["accuracy", "loss", "precision", "fitness"]),
        value=random.uniform(0, 1),
        step=random.randint(1, 1000),
    )

def seed_all(num_projects: int, num_exps_per_project: int, num_trials_per_exp: int, num_runs_per_trial: int, num_metrics_per_run: int):
    Base.metadata.create_all(bind=engine)

    print("🌱 generating seeds ...")
    projects = [generate_project() for _ in range(num_projects)]
    session.add_all(projects)
    session.commit()

    experiments = [generate_experiment(projects) for _ in range(num_exps_per_project)]
    session.add_all(experiments)
    session.commit()

    trials = [generate_trial([exp]) for exp in experiments]
    session.add_all(trials)
    session.commit()

    runs = [generate_run(trials) for _ in range(num_runs_per_trial)]
    session.add_all(runs)
    session.commit()

    metrics = [generate_metric(runs) for _ in range(num_metrics_per_run)]
    session.add_all(metrics)
    session.commit()

    print("🌳 seeding completed.")


if __name__ == "__main__":
    seed_all(num_projects=3, num_exps_per_project=20, num_trials_per_exp=50, num_runs_per_trial=100, num_metrics_per_run=100)
