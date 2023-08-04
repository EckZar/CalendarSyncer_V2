from google.oauth2 import service_account
from google.auth.transport.requests import Request

def get_access_token(user_email):
    credentials = service_account.Credentials.from_service_account_file(
        'secret.json',
        scopes=['https://www.googleapis.com/auth/calendar'],
        subject=user_email
    )
    if not credentials.token:
        credentials.refresh(Request())
    return credentials.token