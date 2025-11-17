# GraphQL Server – Design Document (v0.1)
## 1. Objective

The goal of this feature is to introduce a GraphQL API layer between the dashboard frontend and the existing backend services.
This API will expose read-only experiment data (experiments --> trials --> runs --> metrics) so the dashboard can fetch exactly what it needs with a single query per view.
This is the minimal required step to support the dashboard layout work described in:
Issue #61 – Experiment layout in the dashboard.

## 2. Scope (v0.1)

We incude the following
- A new FastAPI + Strawberry GraphQL server  
- GraphQL schema (read-only)
- Queries implemented in v0.1:

- Queries (The following queries will be implemented in v0.1):
```
    projects
    project(id)
    experiments
    experiment(id)
    trials(experiment_id)
    trial(id)
    runs(trial_id)
    run(id)
    trial_metrics(trial_id)
```

GraphQL resolvers mapped to existing SQLAlchemy models
Add /graphql endpoint


Not included （future versions）:
Mutations, Authetication, Caching, Filtering, Pagination


## 3. Architecture:
Dashboard -->  GraphQL Server (FastAPI + Strawberry) --> Backend Services (SqlAlchemy/ Postgres)


## 4. Schema Proposal (v0.2)
### 4.1 Types
```
type Project {
id: ID!
name: String
description: String
created_at: DateTime
updated_at: DateTime
experiments: [Experiment]
}
type Experiment {
id: ID!
project_id: ID
name: String
description: String
meta: JSON
created_at: DateTime
updated_at: DateTime
trials: [Trial]
}
type Trial {
id: ID!
experiment_id: ID!
meta: JSON
created_at: DateTime
updated_at: DateTime
runs: [Run]
}
type Run {
id: ID!
trial_id: ID!
meta: JSON
created_at: DateTime
}
type Metric {
id: ID!
trial_id: ID!
name: String
value: Float
created_at: DateTime
}
```
### 4.2 Queries
```
type Query {
projects: [Project]
project(id: ID!): Project

experiments: [Experiment]
experiment(id: ID!): Experiment

trials(experiment_id: ID!): [Trial]
trial(id: ID!): Trial

runs(trial_id: ID!): [Run]
run(id: ID!): Run

trial_metrics(trial_id: ID!): [Metric]
}
```
## 5. Directory Structure

This proposal adds a new module `graphql/`:

```
alphatrion/
├── graphql/
│ ├── schema.py
│ ├── resolvers.py
│ └── types.py
└── main.py (mount /graphql endpoint here)
```

API will be mounted as:
POST /graphql
GET  /graphql (playground)

## 6. Integration with FastAPI
Example (v0.1):
```
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from .graphql.schema import schema

app = FastAPI()
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
```

## 7. Security
Not included for v0.1.


## 8. Testing Plan
- Unit tests for each resolver (pytest)
- Integration tests for:
  - projects / project(id)
  - experiments / experiment(id)
  - nested queries (experiment --> trials --> runs)
  - trial_metrics(trial_id)


## 10. Open Questions
- Is read-only sufficient for v0.1?
  (Default assumption: yes, until dashboard requires creation workflows.)
- Do we want nested queries (Experiment --> Trials --> Runs) or only flat queries?
  The frontend can choose whether to use nested or flat queries.


## 11. Summary (TL;DR)
- Implement read-only GraphQL  
- Use FastAPI + Strawberry  
- Expose `/graphql` endpoint  
- Provide queries for:
  - projects  
  - experiments, trials, runs  
  - trial_metrics  
- No mutations in v0.1