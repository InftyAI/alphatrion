from pathlib import Path

from dotenv import load_dotenv

# Load environment variables first
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env.integration-test")
