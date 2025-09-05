import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import datetime
import json


def Create_Service(client_secret, api_name, api_version, *scopes):
    SCOPES = [scope for scope in scopes[0]]
    cred = service_account.Credentials.from_service_account_file(
        client_secret, scopes=SCOPES
    )
    try:
        service = build(api_name, api_version, credentials=cred)
        return service
    except Exception as e:
        print('Unable to connect', api_name, api_version, scopes, sep='-')
        print(e)
        return None