import argparse

import uvicorn
from rich.console import Console
from rich.text import Text
from dotenv import load_dotenv

load_dotenv()
console = Console()

def main():
    parser = argparse.ArgumentParser(description="AlphaTrion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dashboard = subparsers.add_parser("dashboard", help="Run the AlphaTrion dashboard")
    dashboard.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the dashboard on")
    dashboard.add_argument("--port", type=int, default=8000, help="Port to run the dashboard on")
    dashboard.set_defaults(func=run_dashboard)

    args = parser.parse_args()
    args.func(args)

def run_dashboard(args):
    msg = Text(f"Starting AlphaTrion dashboard at http://{args.host}:{args.port}", style="bold green")
    console.print(msg)
    uvicorn.run("alphatrion.cmd.app:app", host=args.host, port=args.port)
