import json

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.core.config import settings


def get_google_access_token() -> str:
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    json_data = json.loads(
        open(settings.GOOGLE_APPLICATION_CREDENTIALS).read()
    )

    credentials = service_account.Credentials.from_service_account_info(
        json_data,
        scopes=scopes,
    )
    credentials.refresh(Request())

    return credentials.token
