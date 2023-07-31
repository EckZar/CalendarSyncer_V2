from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build

def get_access_token(user_email):

    SERVICE_ACCOUNT_PKCS12_FILE_PATH = 'gycalsync.p12'
    SERVICE_ACCOUNT_EMAIL = 'sync-938@gycalsync.iam.gserviceaccount.com'

    credentials = ServiceAccountCredentials.from_p12_keyfile(
        SERVICE_ACCOUNT_EMAIL,
        SERVICE_ACCOUNT_PKCS12_FILE_PATH,
        'notasecret',
        scopes=['https://www.googleapis.com/auth/calendar'])

    credentials = credentials.create_delegated(user_email)
    service = build('calendar', 'v3', credentials=credentials)
    service.events().list(calendarId='primary', maxResults=1).execute()

    return credentials.access_token