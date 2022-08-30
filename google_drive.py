from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from os import getenv
from config_parser import config_parser
from logger import app_logger


google_service = None
SCOPES = ['https://www.googleapis.com/auth/drive']

print(f"id of app logger {id(app_logger)}")

def setup_google_drive_service(func):
    def wrapper(*args, **kwargs):
        global google_service
        if google_service:
            func()
            return
        if not getenv('GOOGLE_DRIVE_AUTH'):
            app_logger.error(
                f"Google Drive won't work properly, need to setup 'GOOGLE_DRIVE_AUTH' variable with service account info")
            return
        service_account_info = json.loads(getenv('GOOGLE_DRIVE_AUTH'))
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES)
        google_service = build('drive', 'v3', credentials=creds)
        app_logger.info(
            f"Google Drive service setup for {SCOPES}")
        return func(*args, **kwargs)
    return wrapper

# TODO save folder names with google drive ids --> maybe in database (dir_name, id, program_id)
# Create basic folder structure and upload when creating new program and generate new contracts


class FileData:
    def __init__(self, _name, _id, _mime_type):
        self.name = _name
        self.id = _id
        self.mime_type = _mime_type
        super().__init__()

    def __str__(self):
        return f"{self.name} id: {self.id} mimeType: {self.mime_type}"


def file_found(name: str, file_list: List[FileData]):
    return name in [file.name for file in file_list]


class GoogleDriveCommands:
    @staticmethod
    @setup_google_drive_service
    def create_directory(parent_directory_id, directory_name):
        try:
            file_metadata = {
                'name': directory_name,
                'parents': [parent_directory_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = google_service.files().create(body=file_metadata, fields='id').execute()
            app_logger.debug(f"Directory has been created with ID: {folder.get('id')}")
        except HttpError as error:
            app_logger.error(f"Error during creation '{directory_name}' in '{parent_directory_id}': {error}")
            return None
        return folder.get("id")

    @staticmethod
    @setup_google_drive_service
    def search(parent_id=config_parser.get('DocTemplates', 'google_drive_id'),
               mime_type_query="='application/vnd.google-apps.folder'",
               recursive_search=True) -> List[FileData]:
        found = []
        page_token = None
        try:
            while True:
                response = google_service.files().list(q=f"mimeType{mime_type_query} and '{parent_id}' in parents",
                                                       spaces="drive",
                                                       fields="nextPageToken,  files(id, name, mimeType)").execute()
                for file in response.get('files', []):
                    found.append(FileData(file.get("name"), file.get("id"), file.get("mimeType")))
                if not recursive_search:
                    break
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except HttpError as error:
            app_logger.error(f"Error during search of mime_type: {error}")
        return found

    @staticmethod
    @setup_google_drive_service
    def upload_file(parent_id='1Sc6UbsrzpAfTq2pq9Ieu7VSn1CGxmGrX', path_to_file=""):
        try:
            file_metadata = {
                'name': "gen/Program_1/Rejestr_29-08-2022.docx",
                'parents': [parent_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = google_service.files().create(body=file_metadata, fields="id").execute()
            print(f"Uploaded or note {file.get('id')}")
        except HttpError as error:
            app_logger.error(f"Error during uploading file '{staticmethod}' in '{parent_id}': {error}")
