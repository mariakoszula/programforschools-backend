from helpers.google_drive import GoogleDriveCommands, GoogleDriveCommandsAsync
from helpers.common import GOOGLE_DRIVE_ID, FileData
from helpers.config_parser import config_parser
import time
import pytest
from os import path
from shutil import copy
import time


def test_google_drive_has_one_directory():
    GoogleDriveCommands.create_directory(GOOGLE_DRIVE_ID, "DUMMY_DIR_NAME")
    time.sleep(5)
    result = GoogleDriveCommands.search()
    assert len(result) == 1


def test_create_and_remove_directory_successful():
    dummy_directory = "DUMMY_NAME"
    directory_id = GoogleDriveCommands.create_directory(GOOGLE_DRIVE_ID, dummy_directory)
    assert directory_id
    time.sleep(3)
    assert dummy_directory in [item.name for item in GoogleDriveCommands.search()]
    GoogleDriveCommands.remove(directory_id)


loop_size = 2


def get_file_to_upload(file_no) -> FileData:
    helper_files_dir = config_parser.get('DocTemplates', 'directory')
    file_name = path.join(helper_files_dir,
                          config_parser.get('DocTemplates', 'test').format(file_no))
    if not path.exists(file_name):
        copy(path.join(helper_files_dir, "test_file.docx"), file_name)
    return FileData(_name=file_name)


file_to_upload_list = [get_file_to_upload(i + 1) for i in range(loop_size)]


def clean_remote_files(file_ids_to_clean):
    for file_id in file_ids_to_clean:
        GoogleDriveCommands.remove(file_id)


def test_upload_file():
    files_to_clean = []
    for file_to_upload in file_to_upload_list:
        (file_id, webViewLink) = GoogleDriveCommands.upload_file(file_to_upload)
        files_to_clean.append(file_id)
        assert file_id is not None
        assert webViewLink is not None
    clean_remote_files(files_to_clean)


file_id_to_export_list = [
    FileData(_name=get_file_to_upload(loop_size).name, _id='1rKb3PXPyTGZvtb8WgS4hcVBKhO7ydb1oty5O6u0CJC4')
    for _ in range(loop_size)]


def test_convert_to_pdf():
    for file_id_to_export in file_id_to_export_list:
        pdf_file_content = GoogleDriveCommands.convert_to_pdf(file_id_to_export.id)
        assert b"PDF" in pdf_file_content


@pytest.mark.asyncio
async def test_google_drive_has_one_directory_async():
    result = await GoogleDriveCommandsAsync.search()
    assert "DUMMY_DIR_NAME" in [item.name for item in result]


@pytest.mark.asyncio
async def test_upload_file_async():
    file = get_file_to_upload(1)
    file_data: FileData = await GoogleDriveCommandsAsync.upload_file(file)
    assert file_data.name == file.name
    assert file_data.web_view_link is not None
    assert file_data.id is not None
    clean_remote_files([file_data.id])


@pytest.mark.asyncio
async def test_upload_many_async():
    files_to_clean = []
    results = await GoogleDriveCommandsAsync.upload_many(file_to_upload_list)
    file_data: FileData
    for file_data in results:
        files_to_clean.append(file_data.id)
        assert file_data.id is not None
        assert file_data.web_view_link is not None
    time.sleep(3)
    clean_remote_files(files_to_clean)


@pytest.mark.asyncio
async def test_convert_to_pdf_async():
    pdf_files = await GoogleDriveCommandsAsync.convert_to_pdf_many(file_id_to_export_list)
    current_file: FileData
    for current_file in pdf_files:
        with open(current_file.name, "rb") as file:
            assert b"PDF" in file.readline()
            assert current_file.id is None
    GoogleDriveCommandsAsync.clear_tmp()
