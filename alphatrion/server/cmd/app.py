from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from alphatrion.server.graphql.schema import schema

app = FastAPI()

# Add CORS middleware - allows frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
