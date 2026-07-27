from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent

DATABASE_FOLDER = ROOT_DIR / "database"
DATABASE_PATH = DATABASE_FOLDER / "corporate.db"

STORAGE_FOLDER = ROOT_DIR / "storage"
PDF_FOLDER = STORAGE_FOLDER / "pdf"
JSON_FOLDER = STORAGE_FOLDER / "json"

OUTPUT_FOLDER = ROOT_DIR / "output"
LOG_FOLDER = ROOT_DIR / "logs"

APP_NAME = "Corporate Intelligence AI"
VERSION = "1.0"

# Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")