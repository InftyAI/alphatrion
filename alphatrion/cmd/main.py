import argparse

import uvicorn
from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text

from alphatrion.graphql.runtime import init as graphql_init

load_dotenv()
console = Console()


def main():
    parser = argparse.ArgumentParser(description="AlphaTrion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server = subparsers.add_parser("server", help="Run the AlphaTrion server")
    server.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the dashboard on"
    )
    server.add_argument(
        "--port", type=int, default=8000, help="Port to run the dashboard on"
    )
    server.set_defaults(func=run_server)

    # Reserve for dashboard command in the future

    args = parser.parse_args()
    args.func(args)


def run_server(args):
    msg = Text(
        f"Starting AlphaTrion server at http://{args.host}:{args.port}",
        style="bold green",
    )
    console.print(msg)
    graphql_init()
    uvicorn.run("alphatrion.cmd.app:app", host=args.host, port=args.port)
