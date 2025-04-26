import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# VertexAI configuration
VERTEX_PROJECT_ID = os.getenv("PROJECT_ID")
VERTEX_LOCATION = os.getenv("LOCATION", "us-central1")
VERTEX_MODEL_ID = os.getenv("MODEL_ID", "gemini-flash-2.5-001")

# Google Sheets configuration
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")

# Paths
SERVICE_ACCOUNT_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    "config/service_accounts/vertex-ai-credentials.json"
)

# Application settings
OCR_CONFIDENCE_THRESHOLD = 0.7
MAX_RETRIES = 3
DEFAULT_TIMEZONE = "UTC"
