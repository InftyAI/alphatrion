#!/usr/bin/env python3
"""
Seed database with test data for dashboard development

This script creates:
- A test user (alice)
- Two teams (Engineering, Data Science)
- Associates user with both teams
- Creates sample projects and experiments

Usage:
    python hack/seed_dashboard_data.py
"""

from dotenv import load_dotenv

load_dotenv()

from alphatrion.server.graphql.runtime import graphql_runtime, init

def seed_data():
    """Seed the database with test data"""
    print("Initializing database...")
    init(init_tables=True)
    metadb = graphql_runtime().metadb

    print("\n1. Creating teams...")
    team1_id = metadb.create_team(
        name="Engineering Team",
        description="Software engineering department",
        meta={"department": "eng", "location": "San Francisco"}
    )
    print(f"   ✓ Created Engineering Team: {team1_id}")

    team2_id = metadb.create_team(
        name="Data Science Team",
        description="Data science and ML department",
        meta={"department": "ds", "location": "New York"}
    )
    print(f"   ✓ Created Data Science Team: {team2_id}")

    print("\n2. Creating test user...")
    try:
        user_id = metadb.create_user(
            username="alice",
            email="alice@example.com",
            meta={"role": "engineer", "level": "senior"}
        )
        print(f"   ✓ Created user 'alice': {user_id}")
    except Exception as e:
        if "duplicate key" in str(e) or "already exists" in str(e):
            # User already exists, query it
            from alphatrion.storage.sql_models import User
            from sqlalchemy import select
            with metadb._session() as session:
                stmt = select(User).where(User.email == "alice@example.com")
                user = session.scalar(stmt)
                if user:
                    user_id = user.uuid
                    print(f"   ℹ User 'alice' already exists: {user_id}")
                else:
                    raise
        else:
            raise

    print("\n3. Adding user to teams...")
    metadb.add_user_to_team(user_id=user_id, team_id=team1_id)
    print(f"   ✓ Added alice to Engineering Team")

    metadb.add_user_to_team(user_id=user_id, team_id=team2_id)
    print(f"   ✓ Added alice to Data Science Team")

    print("\n4. Creating sample projects...")
    project1_id = metadb.create_project(
        name="ML Model Training",
        team_id=team1_id,
        user_id=user_id,
        description="Training and evaluating ML models",
        meta={"type": "ml", "framework": "pytorch"}
    )
    print(f"   ✓ Created project 'ML Model Training': {project1_id}")

    project2_id = metadb.create_project(
        name="Data Pipeline",
        team_id=team1_id,
        user_id=user_id,
        description="ETL pipeline development",
        meta={"type": "data", "tech": "spark"}
    )
    print(f"   ✓ Created project 'Data Pipeline': {project2_id}")

    project3_id = metadb.create_project(
        name="Research Experiments",
        team_id=team2_id,
        user_id=user_id,
        description="Exploratory data science experiments",
        meta={"type": "research"}
    )
    print(f"   ✓ Created project 'Research Experiments': {project3_id}")

    print("\n" + "="*60)
    print("✓ Database seeded successfully!")
    print("="*60)
    print(f"\nUser ID for dashboard: {user_id}")
    print(f"\nStart the dashboard with:")
    print(f"  alphatrion dashboard --userid {user_id}")
    print()

if __name__ == "__main__":
    seed_data()
