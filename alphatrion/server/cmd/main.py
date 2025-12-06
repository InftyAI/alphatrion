import argparse
import os
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from rich.text import Text

from alphatrion.server.graphql.runtime import init as graphql_init

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

    dashboard = subparsers.add_parser("dashboard", help="Run the AlphaTrion dashboard")
    dashboard.add_argument(
        "--port", type=int, default=3000, help="Port to run the dashboard on"
    )
    dashboard.set_defaults(func=start_dashboard)

    args = parser.parse_args()
    args.func(args)


def run_server(args):
    msg = Text(
        f"Starting AlphaTrion server at http://{args.host}:{args.port}",
        style="bold green",
    )
    console.print(msg)
    graphql_init()
    uvicorn.run("alphatrion.server.cmd.app:app", host=args.host, port=args.port)


def start_dashboard(args):
    static_path = Path(__file__).resolve().parents[2] / "static"

    app = FastAPI()
    app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        index_file = os.path.join(static_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "index.html not found"}

    url = f"http://localhost:{args.port}"
    webbrowser.open(url)

    uvicorn.run(app, host="127.0.0.1", port=args.port)
