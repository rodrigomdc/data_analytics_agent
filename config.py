import os
from dotenv import load_dotenv

# Configurações de Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
EXTRACTED_DIR = os.path.join(BASE_DIR, "extracted")
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "data.duckdb")

load_dotenv()

# Chave de API Google Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# LLM Model
LLM_MODEL = "gemini-2.5-flash"
