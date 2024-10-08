from typing import List, Tuple
from abc import ABC, abstractmethod

import google_auth_httplib2
import httplib2
from googleapiclient.http import HttpRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import json
from os import getenv, getcwd, listdir, makedirs, remove


from helpers.logger import app_logger
from helpers.common import FileData, DOCX_MIME_TYPE, PDF_MIME_TYPE, DIR_MIME_TYPE, GOOGLE_DRIVE_ID, get_mime_type, \
    DOCX_EXT, PDF_EXT
from os import path
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
import asyncio

from models.directory_tree import DirectoryTreeModel


def validate_google_env_setup():
    if not getenv('GOOGLE_DRIVE_AUTH'):
        app_logger.error(
            f"Google Drive won't work properly, need to setup 'GOOGLE_DRIVE_AUTH' variable with service account info")
        raise Exception(f"Setup 'GOOGLE_DRIVE_AUTH' variable")


validate_google_env_setup()
SCOPES = ['https://www.googleapis.com/auth/drive']

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


class DriveCommands(ABC):
    @staticmethod
    @abstractmethod
    def upload_file(file: FileData):
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

    @staticmethod
    @abstractmethod
    def prepare_remote_parent(output_directory, file_path):
        pass


class GoogleDriveCommands(DriveCommands):
    @staticmethod
    def prepare_remote_parent(output_directory, file_path):
        from helpers.file_folder_creator import DirectoryCreator, DirectoryCreatorError
        try:
            DirectoryCreator.create_remote_tree(output_directory)
            return DirectoryTreeModel.get_google_parent_directory(file_path)
        except Exception as e:
            app_logger.error(f"During creation of directory tree: {e}")
            raise DirectoryCreatorError()

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
    def search_many(google_id_mime_type_list: List[Tuple[int, str]]):
        set_to_search = set()
        for (google_id, name) in google_id_mime_type_list:
            mime_type = PDF_MIME_TYPE if PDF_EXT in name else DOCX_MIME_TYPE
            set_to_search.add((google_id, get_mime_type(mime_type)))
        results = set()
        for (google_id, mime_type) in set_to_search:
            results.update(GoogleDriveCommands.search(google_id, mime_type))
        return results

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
    def upload_file(file_data: FileData):
        try:
            file_metadata = {
                'name': path.split(file_data.name)[1],
                'parents': [file_data.parent_id],
                'mimeType': file_data.mime_type
            }
            media = MediaFileUpload(file_data.name)
            file = google_service.files().create(body=file_metadata, fields="id,webViewLink",
                                                 media_body=media).execute()
            app_logger.debug(
                f"Uploaded file on google drive {file.get('id')} {file_data.name} parent_id: {file_data.parent_id}"
                f" webViewLink:{file.get('webViewLink')}")
            return file.get("id"), file.get('webViewLink')
        except HttpError as error:
            app_logger.error(f"Error during uploading file '{file_data.name}' in '{file_data.parent_id}': {error}")

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
    def remove(google_id):
        try:
            google_service.files().delete(fileId=google_id).execute()
        except HttpError as error:
            app_logger.error(f"Error during removing directory '{google_id}': {error}")
            raise ValueError(f"'{google_id}' failed to remove")

    @staticmethod
    @setup_google_drive_service
    def clean_main_directory():
        for file_or_folder in GoogleDriveCommands.search():
            try:
                GoogleDriveCommands.remove(file_or_folder.id)
            except HttpError as error:
                app_logger.error(f"Error during removing directory '{file_or_folder}': {error}")
        app_logger.info(f"Google '{GOOGLE_DRIVE_ID}' cleaned")


async def schedule_task(func, list_of_items):
    results = [asyncio.create_task(func(item)) for item in list_of_items]
    return await asyncio.gather(*results)


async def schedule(func, list_of_items, limit=30):
    items = len(list_of_items)
    (loops, reminder) = divmod(items, limit)
    if reminder > 0:
        loops += 1
    results = []
    for i in range(loops):
        start = limit * i
        estimated_end = limit * (i + 1)
        end = items if estimated_end > items else estimated_end
        val = await schedule_task(func, list_of_items[start:end])
        results.extend(val)
    return results


class GoogleDriveCommandsAsync(DriveCommands):
    @staticmethod
    def prepare_remote_parent(output_directory, file_path):
        return GoogleDriveCommands.prepare_remote_parent(output_directory, file_path)

    @staticmethod
    def create_directory(parent_directory_id, directory_name):
        return GoogleDriveCommands.create_directory(parent_directory_id, directory_name)

    tmp_pdf_dir = path.join(getcwd(), "tmp")
    if not path.isdir(tmp_pdf_dir):
        makedirs(tmp_pdf_dir)

    @staticmethod
    def clear_tmp():
        for file in listdir(GoogleDriveCommandsAsync.tmp_pdf_dir):
            remove(path.join(GoogleDriveCommandsAsync.tmp_pdf_dir, file))

    @staticmethod
    async def convert_to_pdf_many(files_data: List[FileData]):
        return await schedule(GoogleDriveCommandsAsync.convert_to_pdf, files_data)

    @staticmethod
    async def convert_to_pdf(file_data: FileData):
        if file_data.id is None:
            raise Exception(f"Source file Id needs to be specified for converting pdf using Google Drive API")
        async with Aiogoogle(service_account_creds=aio_creds) as aiogoogle:
            google_drive = await aiogoogle.discover('drive', 'v3')
            try:
                pdf_name = path.join(GoogleDriveCommandsAsync.tmp_pdf_dir, file_data.name.replace(DOCX_EXT, PDF_EXT).split("/")[-1])

                await aiogoogle.as_service_account(google_drive.files.export(fileId=file_data.id, mimeType=PDF_MIME_TYPE,
                                                                             download_file=pdf_name))

                pdf_file: FileData = FileData(_name=pdf_name, _mime_type=PDF_MIME_TYPE,
                                              _parent_id=file_data.parent_id)
                app_logger.debug(f"Export pdf file on google drive for {file_data.id} Pdf file info: {pdf_file}")
                return pdf_file
            except HttpError as error:
                app_logger.error(f"Error during downloading pdf '{file_data.id}': {error}")
            except Exception as error:
                app_logger.error(f"Error during downloading pdf'{file_data.id}': {error}")


    @staticmethod
    async def upload_many(file_data_list: List[FileData]):
        return await schedule(GoogleDriveCommandsAsync.upload_file, file_data_list)

    @staticmethod
    async def upload_file(file_data: FileData):
        async with Aiogoogle(service_account_creds=aio_creds) as aiogoogle:
            google_drive = await aiogoogle.discover('drive', 'v3')
            try:
                json_body = {
                    'name': path.split(file_data.name)[1],
                    'parents': [file_data.parent_id],
                    'mimeType': file_data.mime_type
                }
                command = google_drive.files.create(validate=True,
                                                    upload_file=file_data.name,
                                                    fields="id,webViewLink",
                                                    includePermissionsForView="published",
                                                    json=json_body)

                response = await aiogoogle.as_service_account(command, full_res=True)
                app_logger.info(
                    f"Uploaded file on google drive {response.json.get('id')} {file_data.name} parent_id: {file_data.parent_id}"
                    f" webViewLink:{response.json.get('webViewLink')}")
                file_data.id = response.json.get("id")
                file_data.web_view_link = response.json.get('webViewLink')
                return file_data
            except HttpError as error:
                app_logger.error(
                    f"Error during uploading file '{file_data.name}' in '{file_data.parent_id}': {error}")
            except Exception as error:
                app_logger.error(f"Error during uploading file '{file_data.id}': {error}")

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
