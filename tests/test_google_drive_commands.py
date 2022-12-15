from helpers.google_drive import GoogleDriveCommands, GOOGLE_DRIVE_ID, GoogleDriveCommandsAsync, DOCX_MIME_TYPE
from helpers.config_parser import config_parser
import asyncio
from os import path
import pytest

pytest_plugins = ('pytest_asyncio',)


def test_google_drive_has_one_directory():
    result = GoogleDriveCommands.search()
    assert len(result) == 1


def test_create_and_remove_directory_successful():
    dummy_directory = "DUMMY_NAME"
    directory_id = GoogleDriveCommands.create_directory(GOOGLE_DRIVE_ID, dummy_directory)
    assert directory_id
    assert dummy_directory in [item.name for item in GoogleDriveCommands.search()]
    GoogleDriveCommands.remove(directory_id)
    assert len(GoogleDriveCommands.search()) == 1


def test_upload_file():
    file_to_upload = path.join(config_parser.get('DocTemplates', 'directory'),
                               config_parser.get('DocTemplates', 'test'))
    (file_id, webVieLink) = GoogleDriveCommands.upload_file(file_to_upload, mime_type=DOCX_MIME_TYPE)
    assert file_id is not None
    assert webVieLink is not None
    GoogleDriveCommands.remove(file_id)


@pytest.mark.asyncio
async def test_google_drive_has_one_directory_async():
    result = await GoogleDriveCommandsAsync.search()
    assert result[0].name == "DEV_PROGRAM_2022_2023_SEMESTR_1"


@pytest.mark.asyncio
async def test_upload_file_async():
    file_to_upload = path.join(config_parser.get('DocTemplates', 'directory'),
                               config_parser.get('DocTemplates', 'test'))
    (file_id, webVieLink) = await GoogleDriveCommandsAsync.upload_file(file_to_upload)
    assert file_id is not None
    assert webVieLink is not None
    GoogleDriveCommands.remove(file_id)
