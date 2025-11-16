# GraphQL Server – Design Document (v0.1)
## 1. Objective

The goal of this feature is to introduce a GraphQL API layer between the dashboard frontend and the existing backend services.
This API will expose read-only experiment data (experiments --> trials --> runs --> metrics) so the dashboard can fetch exactly what it needs with a single query per view.
This is the minimal required step to support the dashboard layout work described in:
Issue #61 – Experiment layout in the dashboard.

## 2. Scope (v0.1)

We incude the following
A new FastAPI + Strawberry GraphQL server
GraphQL schema read-only

Queries:
    experiments
    experiment(uuid)
    trials(experiment_uuid)
    runs(trial_uuid)
    metrics(run_uuid)

GraphQL resolvers mapped to existing SQLAlchemy models
Add /graphql endpoint


Not included （future versions）:
Mutations, Authetication, Caching, Filtering, Pagination


## 3. Architecture:
Dashboard -->  GraphQL Server (FastAPI + Strawberry) --> Backend Services (SqlAlchemy/ Postgres)


## 4. Schema Proposal (v0.1)
### 4.1 Types
```
type Experiment {
  uuid: ID!
  name: String
  description: String
  project_id: ID
  meta: JSON
  created_at: DateTime
  updated_at: DateTime
  trials: [Trial]
}

type Trial {
  uuid: ID!
  experiment_id: ID!
  meta: JSON
  created_at: DateTime
  updated_at: DateTime
  runs: [Run]
}

type Run {
  uuid: ID!
  trial_id: ID!
  meta: JSON
  created_at: DateTime
  metrics: [Metric]
}

type Metric {
  uuid: ID!
  run_id: ID!
  name: String
  value: Float
  created_at: DateTime
}
```
### 4.2 Queries
```
type Query {
  experiments: [Experiment]
  experiment(uuid: ID!): Experiment
  trials(experiment_uuid: ID!): [Trial]
  runs(trial_uuid: ID!): [Run]
  metrics(run_uuid: ID!): [Metric]
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
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from .graphql.schema import schema

app = FastAPI()
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")

## 7. Security
Not included for v0.1.


## 8. Testing Plan
Unit tests for each resolver (pytest)
Integration tests for:
experiments
experiment(uuid)
nested queries (experiment --> trials --> runs)


## 10. Open Questions
Is read-only sufficient for v0.1?
(Default assumption: yes, until dashboard requires creation workflows.)
Do we want nested queries (Experiment --> Trials --> Runs) or only flat queries?



## 11. Summary (TL;DR)
Implement read-only GraphQL.
Use FastAPI + Strawberry.
Expose /graphql endpoint.
Provide queries for experiments, trials, runs, metrics.
No mutations in v0.1.