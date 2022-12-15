from typing import List
from abc import ABC, abstractmethod

import aiofiles.os
import google_auth_httplib2
import httplib2
from googleapiclient.http import HttpRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import json
from os import getenv, getcwd, listdir, makedirs, path, remove
from helpers.config_parser import config_parser
from helpers.logger import app_logger
from os import path
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
from asynctempfile import NamedTemporaryFile
import asyncio


def validate_google_env_setup():
    if not getenv('GOOGLE_DRIVE_AUTH'):
        app_logger.error(
            f"Google Drive won't work properly, need to setup 'GOOGLE_DRIVE_AUTH' variable with service account info")
        raise Exception(f"Setup 'GOOGLE_DRIVE_AUTH' variable")


validate_google_env_setup()
SCOPES = ['https://www.googleapis.com/auth/drive']
DOCX_MIME_TYPE = 'application/vnd.google-apps.document'
PDF_MIME_TYPE = 'application/pdf'
DIR_MIME_TYPE = 'application/vnd.google-apps.folder'
GOOGLE_DRIVE_ID = config_parser.get("GoogleDriveConfig", "google_drive_id")

service_account_key = json.loads(getenv('GOOGLE_DRIVE_AUTH'))
google_service = None
aio_creds = ServiceAccountCreds(scopes=SCOPES, **service_account_key)


def setup_google_drive_service(func):
    def wrapper(*args, **kwargs):
        global google_service
        if google_service:
            return func(*args, **kwargs)

        def build_request(http, *args, **kwargs):
            new_http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())
            return HttpRequest(new_http, *args, **kwargs)

        creds = service_account.Credentials.from_service_account_info(service_account_key,
                                                                      scopes=SCOPES)
        authorized_http = google_auth_httplib2.AuthorizedHttp(credentials=creds, http=httplib2.Http())
        google_service = build('drive', 'v3', requestBuilder=build_request, http=authorized_http)
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
        return f"FileData(_name={self.name}, _mime_type={self.mime_type}, _id={self.id})"


def file_found(name: str, file_list: List[FileData]):
    return name in [file.name for file in file_list]


def get_mime_type(mime_type):
    return f"='{mime_type}'"


class DriveCommands(ABC):
    @staticmethod
    @abstractmethod
    def upload_file(path_to_file,
                    mime_type=get_mime_type(DOCX_MIME_TYPE),
                    parent_id=GOOGLE_DRIVE_ID):
        pass

    @staticmethod
    @abstractmethod
    def convert_to_pdf(source_file_id):
        pass

    @staticmethod
    @abstractmethod
    def search(parent_id=GOOGLE_DRIVE_ID,
               mime_type_query=get_mime_type(DIR_MIME_TYPE),
               recursive_search=True):
        pass

    @staticmethod
    @abstractmethod
    def create_directory(parent_directory_id, directory_name):
        pass


class GoogleDriveCommands(DriveCommands):
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
    def search(parent_id=GOOGLE_DRIVE_ID,
               mime_type_query=get_mime_type(DIR_MIME_TYPE),
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
                    parent_id=GOOGLE_DRIVE_ID):
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
    def convert_to_pdf(source_file_id):
        try:
            pdf_file_content = google_service.files().export(fileId=source_file_id, mimeType=PDF_MIME_TYPE).execute()
            app_logger.debug(f"Export pdf file on google drive for {source_file_id}")
            return pdf_file_content
        except HttpError as error:
            app_logger.error(f"Error during uploading file '{source_file_id}': {error}")

    @staticmethod
    @setup_google_drive_service
    def remove(directory_id):
        try:
            google_service.files().delete(fileId=directory_id).execute()
        except HttpError as error:
            app_logger.error(f"Error during removing directory '{directory_id}': {error}")

    @staticmethod
    @setup_google_drive_service
    def clean_main_directory():
        for file_or_folder in GoogleDriveCommands.search():
            try:
                GoogleDriveCommands.remove(file_or_folder.id)
            except HttpError as error:
                app_logger.error(f"Error during removing directory '{file_or_folder}': {error}")
        app_logger.info(f"Google '{GOOGLE_DRIVE_ID}' cleaned")


class GoogleDriveCommandsAsync(DriveCommands):
    @staticmethod
    def create_directory(parent_directory_id, directory_name):
        raise NotImplementedError(f"Need to be implemented so far problems with aiogoogle how to setup this")

    tmp_pdf_dir = path.join(getcwd(), "tmp")
    if not path.isdir(tmp_pdf_dir):
        makedirs(tmp_pdf_dir)

    @staticmethod
    def clear_tmp():
        for file in listdir(GoogleDriveCommandsAsync.tmp_pdf_dir):
            remove(path.join(GoogleDriveCommandsAsync.tmp_pdf_dir, file))

    @staticmethod
    async def upload_many(file_ids_list):
        pdf_contents = [asyncio.create_task(GoogleDriveCommandsAsync.convert_to_pdf(file_id)) for file_id in
                        file_ids_list]
        return await asyncio.gather(*pdf_contents)

    @staticmethod
    async def convert_to_pdf(source_file_id):
        async with Aiogoogle(service_account_creds=aio_creds) as aiogoogle:
            google_drive = await aiogoogle.discover('drive', 'v3')
            try:
                async with NamedTemporaryFile(dir=GoogleDriveCommandsAsync.tmp_pdf_dir,
                                              delete=False) as file:
                    command = google_drive.files.export(fileId=source_file_id, mimeType=PDF_MIME_TYPE,
                                                        download_file=file.name)
                    await aiogoogle.as_service_account(command, full_res=True)

                    app_logger.debug(f"Export pdf file on google drive for {source_file_id}")
                    return await file.read()
            except HttpError as error:
                app_logger.error(f"Error during uploading file '{source_file_id}': {error}")

    @staticmethod
    async def upload_file(path_to_file,
                          mime_type=get_mime_type(DOCX_MIME_TYPE),
                          parent_id=GOOGLE_DRIVE_ID):
        async with Aiogoogle(service_account_creds=aio_creds) as aiogoogle:
            google_drive = await aiogoogle.discover('drive', 'v3')
            try:
                file_metadata = {
                    'name': path.split(path_to_file)[1],
                    'parents': [parent_id],
                    'mimeType': mime_type
                }
                media = MediaFileUpload(path_to_file)
                command = google_drive.files.create(body=file_metadata,
                                                    fields="id,webViewLink",
                                                    media_body=media,
                                                    upload_file=path_to_file)
                file = await aiogoogle.as_service_account(command)
                app_logger.debug(f"Uploaded file on google drive {file.get('id')} {path_to_file} parent_id: {parent_id}"
                                 f" webViewLink:{file.get('webViewLink')}")
                return file.get("id"), file.get('webViewLink')
            except HttpError as error:
                app_logger.error(f"Error during uploading file '{path_to_file}' in '{parent_id}': {error}")

    @staticmethod
    async def search(parent_id=GOOGLE_DRIVE_ID,
                     mime_type_query=get_mime_type(DIR_MIME_TYPE),
                     recursive_search=True) -> List[FileData]:
        async with Aiogoogle(service_account_creds=aio_creds) as aiogoogle:
            google_drive = await aiogoogle.discover('drive', 'v3')
            found = []
            page_token = None
            try:
                while True:
                    response = await aiogoogle.as_service_account(
                        google_drive.files.list(q=f"mimeType{mime_type_query} and '{parent_id}' in parents",
                                                spaces="drive",
                                                fields="nextPageToken,  files(id, name, mimeType)"))
                    for file in response.get('files', []):
                        new_file = FileData(_name=file.get("name"), _id=file.get("id"), _mime_type=file.get("mimeType"))
                        found.append(new_file)
                    if not recursive_search:
                        break
                    page_token = response.get('nextPageToken', None)
                    if page_token is None:
                        break
            except HttpError as error:
                app_logger.error(f"Error during search of mime_type: {error}")
            return found
