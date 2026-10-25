from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env.test")
