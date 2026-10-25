# GraphQL Server – Design Document (v0.1)
## 1. Objective

The goal of this feature is to introduce a GraphQL API layer between the dashboard frontend and the existing backend services.
This API will expose read-only experiment data (experiments --> runs --> metrics) so the dashboard can fetch exactly what it needs with a single query per view.
Experiments can be organized using labels for grouping and filtering.

## 2. Scope (v0.1)

We incude the following
- A new FastAPI + Strawberry GraphQL server  
- GraphQL schema (read-only)
- Queries implemented in v0.1:

- Queries (The following queries will be implemented in v0.1):
```
    experiments
    experiment(id)
    runs(experiment_id)
    run(id)
    metrics(run_id)
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
type Experiment {
id: ID!
name: String
description: String
meta: JSON
params: JSON
labels: [String]
created_at: DateTime
updated_at: DateTime
runs: [Run]
}
type Run {
id: ID!
experiment_id: ID!
meta: JSON
status: String
created_at: DateTime
metrics: [Metric]
}
type Metric {
id: ID!
run_id: ID!
key: String
value: Float
created_at: DateTime
}
```
### 4.2 Queries
```
type Query {
experiments(labels: [String]): [Experiment]
experiment(id: ID!): Experiment

runs(experiment_id: ID!): [Run]
run(id: ID!): Run

metrics(run_id: ID!): [Metric]
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
  - experiments / experiment(id)
  - nested queries (experiment --> runs --> metrics)
  - metrics(run_id)


## 10. Open Questions
- Is read-only sufficient for v0.1?
  (Default assumption: yes, until dashboard requires creation workflows.)
- Do we want nested queries (Experiment --> Runs --> Metrics) or only flat queries?
  The frontend can choose whether to use nested or flat queries.


## 11. Summary (TL;DR)
- Implement read-only GraphQL
- Use FastAPI + Strawberry
- Expose `/graphql` endpoint
- Provide queries for:
  - experiments (with optional label filtering)
  - runs
  - metrics
- No mutations in v0.1