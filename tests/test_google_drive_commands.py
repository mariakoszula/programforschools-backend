from helpers.google_drive import GoogleDriveCommands, GOOGLE_DRIVE_ID


def test_google_drive_is_empty():
    result = GoogleDriveCommands.search()
    assert len(result) == 0


def test_create_and_remove_directory_successful():
    dummy_directory = "DUMMY_NAME"
    directory_id = GoogleDriveCommands.create_directory(GOOGLE_DRIVE_ID, dummy_directory)
    assert directory_id
    assert dummy_directory == GoogleDriveCommands.search()[0].name
    GoogleDriveCommands.remove(directory_id)
    assert len(GoogleDriveCommands.search()) == 0
