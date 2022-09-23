from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import json
from os import getenv
from helpers.config_parser import config_parser
from helpers.logger import app_logger
from os import path

google_service = None
SCOPES = ['https://www.googleapis.com/auth/drive']
DOCX_MIME_TYPE = 'application/vnd.google-apps.document'
PDF_MIME_TYPE = 'application/pdf'
DIR_MIME_TYPE = 'application/vnd.google-apps.folder'


def setup_google_drive_service(func):
    def wrapper(*args, **kwargs):
        global google_service
        if google_service:
            return func(*args, **kwargs)
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


class FileData:
    def __init__(self, _name, _mime_type, _id=None):
        self.name = _name
        self.mime_type = _mime_type
        self.id = _id
        self.web_view_link = None
        super().__init__()

    def __str__(self):
        return f"{self.name}: webViewLink:{self.web_view_link if self.web_view_link else '-'}"

    def __repr__(self):
        return f"{str(self)} mimeType:{self.mime_type} id:{self.id if self.id else '-'}"


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
            raise ValueError(f"'{directory_name}' failed to create")
        return folder.get("id")

    @staticmethod
    @setup_google_drive_service
    def search(parent_id=config_parser.get('GoogleDriveConfig', 'google_drive_id'),
               mime_type_query=f"='{DIR_MIME_TYPE}'",
               recursive_search=True) -> List[FileData]:
        found = []
        page_token = None
        try:
            while True:
                response = google_service.files().list(q=f"mimeType{mime_type_query} and '{parent_id}' in parents",
                                                       spaces="drive",
                                                       fields="nextPageToken,  files(id, name, mimeType)").execute()
                for file in response.get('files', []):
                    found.append(FileData(_name=file.get("name"), _id=file.get("id"), _mime_type=file.get("mimeType")))
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
    def upload_file(path_to_file,
                    mime_type='application/vnd.google-apps.folder',
                    parent_id='1Sc6UbsrzpAfTq2pq9Ieu7VSn1CGxmGrX'):
        try:
            file_metadata = {
                'name': path.split(path_to_file)[1],
                'parents': [parent_id],
                'mimeType': mime_type
            }
            media = MediaFileUpload(path_to_file)
            file = google_service.files().create(body=file_metadata, fields="id,webViewLink",
                                                 media_body=media).execute()
            app_logger.debug(f"Uploaded file on google drive {file.get('id')} {path_to_file} parent_id: {parent_id}"
                             f" webViewLink:{file.get('webViewLink')}")
            return file.get("id"), file.get('webViewLink')
        except HttpError as error:
            app_logger.error(f"Error during uploading file '{path_to_file}' in '{parent_id}': {error}")

    @staticmethod
    @setup_google_drive_service
    def export_to_pdf(source_file_id):
        try:
            pdf_file_content = google_service.files().export(fileId=source_file_id, mimeType=PDF_MIME_TYPE).execute()
            app_logger.debug(f"Export pdf file on google drive for {source_file_id}")
            return pdf_file_content
        except HttpError as error:
            app_logger.error(f"Error during uploading file '{source_file_id}': {error}")
