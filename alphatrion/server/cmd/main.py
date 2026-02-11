# ruff: noqa: E501

import argparse
import os
import threading
import time
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from faker import Faker
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from rich.text import Text

from alphatrion import envs
from alphatrion.storage import runtime

load_dotenv()
console = Console()

try:
    __version__ = version("alphatrion")
except PackageNotFoundError:
    __version__ = "unknown"


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

    dashboard = subparsers.add_parser(
        "dashboard", help="Launch the AlphaTrion web dashboard"
    )
    dashboard.add_argument(
        "--port",
        type=int,
        default=5173,
        help="Port to run the dashboard on (default: 5173)",
    )
    dashboard.add_argument(
        "--backend-url",
        type=str,
        default="http://localhost:8000",
        help="Backend server URL to proxy requests to (default: http://localhost:8000)",
    )
    dashboard.add_argument(
        "--userid",
        type=str,
        default=os.getenv(envs.DASHBOARD_USER_ID),
        help="User ID to scope the dashboard (required)",
    )
    dashboard.set_defaults(func=start_dashboard)

    # init command
    init = subparsers.add_parser(
        "init", help="Initialize AlphaTrion with a user and team"
    )
    init.add_argument(
        "--username",
        type=str,
        default=None,
        help="Username for the new user (auto-generated if not provided)",
    )
    init.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email for the new user (auto-generated if not provided)",
    )
    init.add_argument(
        "--teamname",
        type=str,
        default="Default Team",
        help="Team name (default: Default Team)",
    )
    init.set_defaults(func=init_command)

    # version command
    version = subparsers.add_parser("version", help="Show the version of AlphaTrion")
    version.set_defaults(func=lambda args: print(f"AlphaTrion version {__version__}"))

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


def init_command(args):
    """Initialize AlphaTrion with a user and team."""
    # Initialize the Server runtime to get access to metadb
    runtime.init()

    fake = Faker()

    # Generate username if not provided
    username = args.username if args.username else fake.name()
    email = (
        args.email
        if args.email
        else f"{username.lower().replace(' ', '.')}@inftyai.com"
    )
    teamname = args.teamname

    try:
        metadb = runtime.storage_runtime().metadb

        console.print()
        # Create user
        console.print(
            Text(f"👤 Creating user: {username} ({email})", style="bold cyan")
        )
        user_id = metadb.create_user(username=username, email=email)

        # Create team
        console.print(Text(f"🏢 Creating team: {teamname}", style="bold cyan"))
        team_id = metadb.create_team(name=teamname, description=f"Team for {username}")

        # Add user to team
        metadb.add_user_to_team(user_id=user_id, team_id=team_id)

        console.print()
        console.print(Text("✅ Initialization successful!", style="bold green"))
        console.print()
        console.print(Text("📋 Your user ID:", style="bold yellow"))
        console.print(Text(f"   {user_id}", style="bold cyan"))
        console.print(Text("   Your team ID:", style="bold yellow"))
        console.print(Text(f"   {team_id}", style="bold cyan"))
        console.print()
        console.print(Text("💡 Use this user ID to launch the dashboard, "
            "or set the ALPHATRION_DASHBOARD_USER_ID environment variable", style="dim"))
        console.print(
            Text(f"   alphatrion dashboard --userid {user_id}", style="magenta")
        )
        console.print()
        console.print(
            Text(
                "🚀 Use this user ID and team ID to setup the experiment environment:",
                style="dim",
            )
        )
        console.print(Text("   import alphatrion as alpha", style="white"))
        console.print(
            Text(
                f"   alpha.init(user_id='{user_id}')",
                style="white",
            )
        )
        console.print()

    except Exception as e:
        console.print(Text(f"❌ Error during initialization: {e}", style="bold red"))
        raise


def run_server(args):
    BLUE = "\033[94m"
    RESET = "\033[0m"

    ascii_art = r"""
    █████████   ████            █████                ███████████            ███
   ███░░░░░███ ░░███           ░░███                ░█░░░███░░░█           ░░░
  ░███    ░███  ░███  ████████  ░███████    ██████  ░   ░███  ░  ████████  ████   ██████  ████████
  ░███████████  ░███ ░░███░░███ ░███░░███  ░░░░░███     ░███    ░░███░░███░░███  ███░░███░░███░░███
  ░███░░░░░███  ░███  ░███ ░███ ░███ ░███   ███████     ░███     ░███ ░░░  ░███ ░███ ░███ ░███ ░███
  ░███    ░███  ░███  ░███ ░███ ░███ ░███  ███░░███     ░███     ░███      ░███ ░███ ░███ ░███ ░███
  █████   █████ █████ ░███████  ████ █████░░████████    █████    █████     █████░░██████  ████ █████
 ░░░░░   ░░░░░ ░░░░░  ░███░░░  ░░░░ ░░░░░  ░░░░░░░░    ░░░░░    ░░░░░     ░░░░░  ░░░░░░  ░░░░ ░░░░░
                      ░███
                      █████
                     ░░░░░
    """

    print(f"{BLUE}{ascii_art}{RESET}")

    msg = Text(
        f"Starting AlphaTrion server at http://{args.host}:{args.port}",
        style="bold green",
    )
    console.print(msg)
    runtime.init()
    uvicorn.run("alphatrion.server.cmd.app:app", host=args.host, port=args.port)


def start_dashboard(args):
    BLUE = "\033[94m"
    RESET = "\033[0m"

    ascii_art = r"""
    █████████   ████            █████                ███████████            ███
   ███░░░░░███ ░░███           ░░███                ░█░░░███░░░█           ░░░
  ░███    ░███  ░███  ████████  ░███████    ██████  ░   ░███  ░  ████████  ████   ██████  ████████
  ░███████████  ░███ ░░███░░███ ░███░░███  ░░░░░███     ░███    ░░███░░███░░███  ███░░███░░███░░███
  ░███░░░░░███  ░███  ░███ ░███ ░███ ░███   ███████     ░███     ░███ ░░░  ░███ ░███ ░███ ░███ ░███
  ░███    ░███  ░███  ░███ ░███ ░███ ░███  ███░░███     ░███     ░███      ░███ ░███ ░███ ░███ ░███
  █████   █████ █████ ░███████  ████ █████░░████████    █████    █████     █████░░██████  ████ █████
 ░░░░░   ░░░░░ ░░░░░  ░███░░░  ░░░░ ░░░░░  ░░░░░░░░    ░░░░░    ░░░░░     ░░░░░  ░░░░░░  ░░░░ ░░░░░
                      ░███
                      █████
                     ░░░░░
    """

    print(f"{BLUE}{ascii_art}{RESET}")

    # Find the dashboard static directory
    # Try multiple possible locations
    current_file = Path(__file__).resolve()
    possible_paths = [
        current_file.parents[3]
        / "dashboard"
        / "static",  # Development: alphatrion/alphatrion/server/cmd/main.py -> alphatrion/dashboard/static
        Path.cwd() / "dashboard" / "static",  # If running from project root
        Path.cwd() / "static",  # If running from dashboard directory
    ]

    static_path = None
    for path in possible_paths:
        if path.exists() and (path / "index.html").exists():
            static_path = path
            break

    if static_path is None:
        console.print(
            Text("❌ Error: Dashboard static files not found!", style="bold red")
        )
        console.print(
            Text(
                "Please ensure the dashboard has been built by running:",
                style="yellow",
            )
        )
        console.print(Text("  cd dashboard && npm run build", style="cyan"))
        return

    msg = Text(
        f"🚀 Starting AlphaTrion Dashboard at http://127.0.0.1:{args.port}",
        style="bold green",
    )
    console.print(msg)
    console.print(Text(f"📂 Serving static files from: {static_path}", style="dim"))

    console.print(
        Text(f"🔗 Proxying backend requests to: {args.backend_url}", style="dim")
    )
    console.print(Text(f"👤 Dashboard scoped to user: {args.userid}", style="yellow"))
    console.print()
    console.print(
        Text("💡 Note: Make sure the backend server is running:", style="bold yellow")
    )
    console.print(Text("   alphatrion server", style="cyan"))
    console.print()

    app = FastAPI()

    if not args.userid:
        console.print(
            Text("❌ Error: User ID is required to launch the dashboard!", style="bold red")
        )
        console.print(
            Text(
                "Please provide a user ID using the --userid argument or set the ALPHATRION_DASHBOARD_USER_ID environment variable.",
                style="yellow",
            )
        )
        console.print(
            Text(
                "You can create a user and get their ID by running: alphatrion init",
                style="cyan",
            )
        )
        return
    # Store user ID in app state
    app.state.user_id = args.userid

    # Create HTTP client for proxying requests to backend
    http_client = httpx.AsyncClient(base_url=args.backend_url, timeout=30.0)

    # Endpoint to get current user ID (for frontend)
    @app.get("/api/config")
    async def get_config():
        return {"userId": app.state.user_id}

    # Proxy /graphql requests to backend (MUST be before catch-all route)
    @app.api_route("/graphql", methods=["GET", "POST"])
    async def proxy_graphql(request: Request):
        headers = dict(request.headers)
        headers.pop("host", None)  # Remove host header

        try:
            response = await http_client.request(
                method=request.method,
                url="/graphql",
                content=await request.body(),
                headers=headers,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except Exception as e:
            console.print(Text(f"❌ Error connecting to backend: {e}", style="red"))
            return Response(
                content=f'{{"error": "Backend server not available. Make sure it\'s running at {args.backend_url}"}}',
                status_code=503,
                media_type="application/json",
            )

    # Proxy /api requests to backend (MUST be before catch-all route)
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def proxy_api(path: str, request: Request):
        headers = dict(request.headers)
        headers.pop("host", None)

        try:
            response = await http_client.request(
                method=request.method,
                url=f"/api/{path}",
                content=await request.body(),
                headers=headers,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except Exception as e:
            console.print(Text(f"❌ Error connecting to backend: {e}", style="red"))
            return Response(
                content='{"error": "Backend server not available"}',
                status_code=503,
                media_type="application/json",
            )

    # Mount the entire static directory at /static
    app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

    @app.get("/")
    def serve_root():
        # Serve index.html at root
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "index.html not found"}

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # Serve index.html for all routes (SPA fallback)
        # This enables client-side routing
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "index.html not found"}

    # Register cleanup handler for HTTP client
    @app.on_event("shutdown")
    async def shutdown_event():
        await http_client.aclose()

    url = f"http://127.0.0.1:{args.port}"

    console.print(Text(f"🌐 Dashboard URL: {url}", style="bold cyan"))

    # Open browser after a short delay to ensure server is ready
    def open_browser():
        time.sleep(1)  # Wait for server to start
        webbrowser.open(url)

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    except KeyboardInterrupt:
        console.print(Text("\n👋 Dashboard stopped", style="bold yellow"))
