import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # Default to SQLite for development
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "")
DB_NAME = os.getenv("DB_NAME", "social_media_alert")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct database URL
if DB_TYPE == "sqlite":
    DATABASE_URL = f"sqlite:////{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', f'{DB_NAME}.db'))}"
else:
    DATABASE_URL = f"{DB_TYPE}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Scraper configuration
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"

# Facebook configuration
FACEBOOK_COOKIES = os.getenv("FACEBOOK_COOKIES", "")
FACEBOOK_EMAIL = os.getenv("FACEBOOK_EMAIL", "")
FACEBOOK_PASSWORD = os.getenv("FACEBOOK_PASSWORD", "")

# Nextdoor configuration
NEXTDOOR_COOKIES = os.getenv("NEXTDOOR_COOKIES", "")
NEXTDOOR_EMAIL = os.getenv("NEXTDOOR_EMAIL", "")
NEXTDOOR_PASSWORD = os.getenv("NEXTDOOR_PASSWORD", "")

# Notification configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "alerts@socialmediaalert.com")

# Web application configuration
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
