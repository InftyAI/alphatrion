# ruff: noqa: E501

import argparse
import threading
import time
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from faker import Faker
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from rich.text import Text

from alphatrion.framework.storage import runtime
from alphatrion.framework.utils import log

load_dotenv()
console = Console()

character_length_at_least = 6

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
        "dashboard",
        help="Serve pre-built dashboard (for testing production builds locally)",
    )
    dashboard.add_argument(
        "--port",
        type=int,
        default=5173,
        help="Port to serve the dashboard on (default: 5173)",
    )
    dashboard.set_defaults(func=start_dashboard)

    # init command
    init = subparsers.add_parser(
        "init", help="Initialize AlphaTrion with a user and team"
    )
    init.add_argument(
        "--user-name",
        type=str,
        default=None,
        help="Username for the new user (will prompt if not provided)",
    )
    init.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email for the new user (will prompt if not provided)",
    )
    init.add_argument(
        "--password",
        type=str,
        default=None,
        help="Password for the new user (will prompt if not provided)",
    )
    init.add_argument(
        "--team-name",
        type=str,
        default=None,
        help="Team name (will prompt if not provided, defaults to 'Default Team')",
    )
    init.add_argument(
        "--org-name",
        type=str,
        default=None,
        help="Organization name (will prompt if not provided, auto-generated if empty)",
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
    import getpass

    from alphatrion.framework.server.auth import hash_password

    # Initialize the Server runtime to get access to metadb
    runtime.init()

    fake = Faker()

    # Prompt for user info if not provided
    user_name = args.user_name
    if not user_name:
        user_name = console.input(Text("👤 Enter user name: ", style="cyan"))
        if not user_name:
            user_name = fake.name()
            console.print(Text(f"   Using generated name: {user_name}", style="dim"))

    email = args.email
    if not email:
        email = console.input(Text("📧 Enter email address: ", style="cyan"))
        if not email:
            email = f"{user_name.lower().replace(' ', '.')}@inftyai.com"
            console.print(Text(f"   Using generated email: {email}", style="dim"))

    password = args.password
    if not password:
        console.print(Text("🔐 Enter password for the user:", style="cyan"))
        password = getpass.getpass("   Password: ")
        if not password:
            console.print(
                Text(
                    "❌ Error: Password is required for authentication",
                    style="bold red",
                )
            )
            return
        confirm = getpass.getpass("   Confirm password: ")
        if password != confirm:
            console.print(Text("❌ Error: Passwords do not match", style="bold red"))
            return

    if len(password) < character_length_at_least:
        console.print(
            Text(
                f"❌ Error: Password must be at least {character_length_at_least} characters",
                style="bold red",
            )
        )
        return

    org_name = args.org_name
    if not org_name:
        org_name = console.input(
            Text(
                "🏢 Enter organization name (press Enter to auto-generate): ",
                style="cyan",
            )
        )
        if not org_name:
            org_name = fake.company()
            console.print(
                Text(f"   Using generated organization: {org_name}", style="dim")
            )

    team_name = args.team_name
    if not team_name:
        team_name = console.input(
            Text("👥 Enter team name (press Enter for 'Default Team'): ", style="cyan")
        )
        if not team_name:
            team_name = "Default Team"
            console.print(Text(f"   Using default team: {team_name}", style="dim"))

    # Hash password
    password_hash = hash_password(password)

    try:
        metadb = runtime.storage_runtime().metadb

        console.print()
        # Create organization
        console.print(Text(f"🏢 Creating organization: {org_name}", style="bold cyan"))
        org_id = metadb.create_organization(name=org_name)

        # Create user with password
        console.print(
            Text(f"👤 Creating user: {user_name} ({email})", style="bold cyan")
        )
        user_id = metadb.create_user(
            name=user_name, email=email, org_id=org_id, password_hash=password_hash
        )

        # Create team
        console.print(Text(f"🏢 Creating team: {team_name}", style="bold cyan"))
        team_id = metadb.create_team(
            name=team_name, description=f"Team for {user_name}", org_id=org_id
        )
        # Add user to team
        metadb.add_user_to_team(user_id=user_id, team_id=team_id)

        console.print()
        console.print(Text("✅ Initialization successful!", style="bold green"))
        console.print()
        console.print(Text("📋 Account Information:", style="bold yellow"))
        console.print(Text(f"   Email: {email}", style="cyan"))
        console.print(Text(f"   User ID: {user_id}", style="cyan"))
        console.print(Text(f"   Organization ID: {org_id}", style="cyan"))
        console.print(Text(f"   Team ID: {team_id}", style="cyan"))
        console.print()
        console.print(Text("🚀 Next steps:", style="bold yellow"))
        console.print(Text("   1. Start the backend server:", style="dim"))
        console.print(Text("      alphatrion server", style="white"))
        console.print()
        console.print(Text("   2. Start the dashboard:", style="dim"))
        console.print(Text("      alphatrion dashboard", style="white"))
        console.print()
        console.print(
            Text("   3. Visit http://localhost:5173 and login with:", style="dim")
        )
        console.print(Text(f"      Email: {email}", style="white"))
        console.print(Text("      Password: <your password>", style="white"))
        console.print()
        console.print(
            Text(
                "💡 To use in Python experiments:",
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

    # Configure logging before starting the server
    log.configure_logging()

    runtime.init()
    uvicorn.run(
        "alphatrion.framework.server.cmd.app:app", host=args.host, port=args.port
    )


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
        current_file.parents[2]
        / "dashboard"
        / "static",  # Development: alphatrion/framework/server/cmd/main.py -> alphatrion/framework/dashboard/static
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
        console.print(
            Text("  cd alphatrion/framework/dashboard && npm run build", style="cyan")
        )
        return

    msg = Text(
        f"🚀 Starting AlphaTrion Dashboard at http://127.0.0.1:{args.port}",
        style="bold green",
    )
    console.print(msg)
    console.print(Text(f"📂 Serving static files from: {static_path}", style="dim"))
    console.print()
    console.print(
        Text(
            "💡 Note: Make sure the backend server is running at http://localhost:8000",
            style="bold yellow",
        )
    )
    console.print(Text("   Run: alphatrion server", style="cyan"))
    console.print()

    app = FastAPI()

    # Mount the entire static directory at /static
    app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

    # SPA fallback: serve index.html for all routes (enables client-side routing)
    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "index.html not found"}

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
