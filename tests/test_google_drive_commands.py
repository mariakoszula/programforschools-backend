from helpers.google_drive import GoogleDriveCommands, GOOGLE_DRIVE_ID, GoogleDriveCommandsAsync, DOCX_MIME_TYPE
from helpers.config_parser import config_parser
import time
from os import path
import pytest


def test_google_drive_has_one_directory():
    result = GoogleDriveCommands.search()
    assert len(result) == 1


def test_create_and_remove_directory_successful():
    dummy_directory = "DUMMY_NAME"
    directory_id = GoogleDriveCommands.create_directory(GOOGLE_DRIVE_ID, dummy_directory)
    assert directory_id
    time.sleep(3)
    assert dummy_directory in [item.name for item in GoogleDriveCommands.search()]
    GoogleDriveCommands.remove(directory_id)


file_to_upload = path.join(config_parser.get('DocTemplates', 'directory'),
                           config_parser.get('DocTemplates', 'test'))


def test_upload_file():
    (file_id, webVieLink) = GoogleDriveCommands.upload_file(file_to_upload, mime_type=DOCX_MIME_TYPE)
    assert file_id is not None
    assert webVieLink is not None
    GoogleDriveCommands.remove(file_id)


loop_size = 20
file_id_to_export_list = ['1rKb3PXPyTGZvtb8WgS4hcVBKhO7ydb1oty5O6u0CJC4' for _ in range(loop_size)]


def test_convert_to_pdf():
    for file_id_to_export in file_id_to_export_list:
        pdf_file_content = GoogleDriveCommands.convert_to_pdf(file_id_to_export)
        assert b"PDF" in pdf_file_content


@pytest.mark.asyncio
async def test_google_drive_has_one_directory_async():
    result = await GoogleDriveCommandsAsync.search()
    assert "DEV_PROGRAM_2022_2023_SEMESTR_1" in [item.name for item in result]


@pytest.mark.asyncio
async def test_upload_file_async():
    (file_id, webVieLink) = await GoogleDriveCommandsAsync.upload_file(file_to_upload)
    assert file_id is not None
    assert webVieLink is not None
    GoogleDriveCommands.remove(file_id)


@pytest.mark.asyncio
async def test_convert_to_pdf_async():
    results = await GoogleDriveCommandsAsync.upload_many(file_id_to_export_list)
    assert all([b"PDF" in item for item in results])
    GoogleDriveCommandsAsync.clear_tmp()
