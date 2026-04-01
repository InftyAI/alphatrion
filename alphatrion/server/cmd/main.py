# ruff: noqa: E501

import argparse
import os
import shlex
import subprocess
import threading
import time
import uuid
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

from alphatrion.storage import runtime
from alphatrion.utils import log

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

    # run command (with subcommands)
    run = subparsers.add_parser("run", help="Run agent commands")
    run_subparsers = run.add_subparsers(dest="run_command", required=True)

    # run agent command
    run_agent = run_subparsers.add_parser(
        "agent",
        help="Run an agent with automatic tracking",
    )
    run_agent.add_argument(
        "agent_type",
        type=str,
        choices=["claude", "codex"],
        help="Type of agent to run (e.g., claude, codex)",
    )
    run_agent.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="User ID for this agent session",
    )
    run_agent.add_argument(
        "--team-id",
        type=str,
        default=None,
        help="Team ID for this agent session (optional, auto-detected from user's first team)",
    )
    run_agent.add_argument(
        "--command",
        type=str,
        default=None,
        help="Command to run (defaults to agent type, e.g., 'claude' for claude agent)",
    )
    run_agent.set_defaults(func=run_agent_command)

    # claude-hook command (handles Claude Code hooks)
    claude_hook = subparsers.add_parser(
        "claude-hook", help="Handle Claude Code hooks (called by Claude Code)"
    )
    claude_hook.add_argument(
        "action",
        type=str,
        choices=["session-start", "stop"],
        help="Hook action: session-start (new session), stop (after response)",
    )
    claude_hook.set_defaults(func=handle_claude_hook)

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

    from alphatrion.server.auth import hash_password

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
            Text(f"❌ Error: Password must be at least {character_length_at_least} characters", style="bold red")
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


def run_agent_command(args):
    """Run agent with automatic tracking."""
    from alphatrion.storage.sql_models import AgentType

    # Initialize runtime first
    runtime.init()

    try:
        metadb = runtime.storage_runtime().metadb

        user_id = args.user_id
        team_id = args.team_id

        # If no team_id provided, get user's first team
        if not team_id:
            user_teams = metadb.get_team_members_by_user_id(user_id=uuid.UUID(user_id))
            if not user_teams:
                console.print(
                    Text(
                        "❌ No teams found for user. Please specify --team-id",
                        style="bold red",
                    )
                )
                return
            team_id = str(user_teams[0].team_id)
            console.print(Text(f"📋 Using team: {team_id}", style="dim"))

        # Map agent type string to enum
        agent_type_map = {
            "claude": AgentType.CLAUDE,
            # "codex": AgentType.CODEX,  # Future: add more agent types here
        }
        agent_type = agent_type_map.get(args.agent_type.lower())

        if not agent_type:
            console.print(
                Text(f"❌ Unknown agent type: {args.agent_type}", style="bold red")
            )
            return

        # Agent name is always the same as agent type
        agent_name = args.agent_type.lower()

        # Determine command to run (defaults to agent type)
        command = args.command if args.command else agent_name

        # Check if agent with same name and type already exists
        existing_agent = metadb.get_agent_by_type(
            user_id=uuid.UUID(user_id),
            agent_type=agent_type,
        )

        if existing_agent:
            agent_id = existing_agent.uuid
            console.print(
                Text(f"🤖 Using existing agent: {agent_name}", style="bold cyan")
            )
            console.print(Text(f"   Agent ID: {agent_id}", style="dim"))
        else:
            console.print(
                Text(f"🤖 Creating new agent: {agent_name}", style="bold cyan")
            )
            agent_id = metadb.create_agent(
                name=agent_name,
                type=agent_type,
                org_id=metadb.get_user(uuid.UUID(user_id)).org_id,
                team_id=uuid.UUID(team_id),
                user_id=uuid.UUID(user_id),
            )
            console.print(Text(f"   Agent ID: {agent_id}", style="dim"))

        console.print()
        console.print(
            Text(
                "✅ Agent ready! Environment variables set for hooks.",
                style="bold green",
            )
        )
        console.print()
        console.print(Text(f"   ALPHATRION_USER_ID={user_id}", style="dim"))
        console.print(Text(f"   ALPHATRION_TEAM_ID={team_id}", style="dim"))
        console.print(Text(f"   ALPHATRION_AGENT_ID={agent_id}", style="dim"))
        console.print()
        console.print(
            Text("📋 Recommended Claude Code hooks configuration:", style="bold yellow")
        )
        console.print(Text("   Add this to ~/.claude/settings.json:", style="dim"))
        console.print()

        hooks_config = """{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "alphatrion claude-hook session-start",
            "stdin": {
              "session_id": "{{ session_id }}",
              "transcript_path": "{{ transcript_path }}",
              "source": "{{ source }}",
              "model": "{{ model }}"
            }
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "alphatrion claude-hook stop",
            "stdin": {
              "session_id": "{{ session_id }}",
              "transcript_path": "{{ transcript_path }}"
            }
          }
        ]
      }
    ]
  }
}"""
        console.print(Text(hooks_config, style="cyan"))
        console.print()
        console.print(Text(f"🚀 Launching {command}...", style="bold green"))
        console.print(
            Text("   (Hooks will automatically track your conversations)", style="dim")
        )
        console.print()

        # Set environment variables for hooks to access (since they run in separate processes)
        os.environ["ALPHATRION_USER_ID"] = user_id
        os.environ["ALPHATRION_TEAM_ID"] = team_id
        os.environ["ALPHATRION_AGENT_ID"] = str(agent_id)

        # Launch command with environment variables inherited
        try:
            subprocess.run(shlex.split(command), check=False, env=os.environ.copy())
        except FileNotFoundError:
            console.print(
                Text(
                    f"❌ '{command}' command not found. Please install it first.",
                    style="bold red",
                )
            )
            return
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            console.print()
            console.print(Text(f"⏹️  {command} session ended", style="bold yellow"))

    except Exception as e:
        console.print(Text(f"❌ Error starting agent session: {e}", style="bold red"))
        raise


def handle_claude_hook(args):
    """Handle Claude Code hooks (SessionStart, Stop, SessionEnd)."""
    from alphatrion.agents.claude import handle_hook

    handle_hook(args.action)


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
    console.print()
    console.print(
        Text("💡 Note: Make sure the backend server is running:", style="bold yellow")
    )
    console.print(Text("   alphatrion server", style="cyan"))
    console.print()

    app = FastAPI()

    # Create HTTP client for proxying requests to backend
    http_client = httpx.AsyncClient(base_url=args.backend_url, timeout=30.0)

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
