from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from alphatrion.graphql.schema import schema

app = FastAPI()

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Mount /graphql endpoint
app.include_router(graphql_app, prefix="/graphql")


# root endpoint for testing
@app.get("/")
def root():
    return {"message": "AlphaTrion API running"}
