from importlib.metadata import version

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from alphatrion.graphql.schema import schema

app = FastAPI()

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Mount /graphql endpoint
app.include_router(graphql_app, prefix="/graphql")


# health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# version endpoint
@app.get("/version")
def get_version():
    return {"version": version("alphatrion"), "status": "ok"}
