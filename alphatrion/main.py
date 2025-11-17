from .graphql.schema import schema
from fastapi import FastAPI
from dotenv import load_dotenv
from strawberry.fastapi import GraphQLRouter

load_dotenv()


app = FastAPI()

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Mount /graphql endpoint
app.include_router(graphql_app, prefix="/graphql")


# root endpoint for testing
@app.get("/")
def root():
    return {"message": "AlphaTrion API running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
