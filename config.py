from dotenv import load_dotenv
import os

load_dotenv()

WEATHERLINK_API_KEY = os.getenv("WEATHERLINK_API_KEY")
WEATHERLINK_API_SECRET = os.getenv("WEATHERLINK_API_SECRET")

LABGURU_BASE_URL = os.getenv("LABGURU_BASE_URL")
LABGURU_TOKEN = os.getenv("LABGURU_TOKEN")

LABGURU_PARENT_FOLDER_ID = os.getenv(
    "LABGURU_PARENT_FOLDER_ID"
)

DRY_RUN = os.getenv(
    "DRY_RUN",
    "true"
).lower() == "true"

AUTO_ADD_COLUMNS = os.getenv(
    "AUTO_ADD_COLUMNS",
    "true"
).lower() == "true"