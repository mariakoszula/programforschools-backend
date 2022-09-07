from typing import List

from helpers.config_parser import config_parser
from models.program import ProgramModel
from models.directory_tree import DirectoryTreeModel
from helpers.google_drive import GoogleDriveCommands, FileData
from helpers.logger import app_logger
from collections import namedtuple

directory_to_create_list = [
    config_parser.get('Directories', 'school'),
    config_parser.get('Directories', 'annex'),
    config_parser.get('Directories', 'contract'),
    config_parser.get('Directories', 'application'),
    config_parser.get('Directories', 'record')
]

CreateDirectoryResults = namedtuple("CreateDirectoryResults", "should_insert directoryTreeObj")


class DirectoryCreator:
    @staticmethod
    def get_main_dir(school_year: str, semester_no: int):
        return f"{config_parser.get('Directories', 'main_dir_program_part')}_" \
               f"{DirectoryCreator.get_part_with_year_and_sem(school_year, semester_no)}"

    @staticmethod
    def get_part_with_year_and_sem(school_year: str, semester_no: int):
        if "/" in school_year:
            school_year = school_year.replace("/", "_")
        return f"{school_year}_" \
               f"{config_parser.get('Directories', 'main_sem_dir_part')}_{semester_no}"

    @staticmethod
    def create_main_directory_tree(program: ProgramModel) -> DirectoryTreeModel:
        main_dir_name = DirectoryCreator.get_main_dir(program.school_year, program.semester_no)
        try:
            google_drive_id = config_parser.get('GoogleDriveConfig', 'google_drive_id')
            main_dir_results: CreateDirectoryResults = DirectoryCreator.create_directory(name=main_dir_name,
                                                                                         program_id=program.id,
                                                                                         google_id=google_drive_id)
            if main_dir_results.should_insert:
                return main_dir_results.directoryTreeObj
        except ValueError:
            raise

    @staticmethod
    def create_directory_tree(program: ProgramModel, main_dir_obj: DirectoryTreeModel) -> List[DirectoryTreeModel]:
        try:
            data_to_update_in_database = []
            for directory_name in directory_to_create_list:
                result = DirectoryCreator.create_directory(name=directory_name,
                                                           program_id=program.id,
                                                           google_id=main_dir_obj.google_id,
                                                           parent_id=main_dir_obj.id)
                if result.should_insert:
                    data_to_update_in_database.append(result.directoryTreeObj)
            return data_to_update_in_database
        except ValueError:
            raise

    @staticmethod
    def create_directory(**kwargs) -> CreateDirectoryResults:
        directories = GoogleDriveCommands.search(parent_id=kwargs["google_id"])
        for file_data in directories:
            if file_data.name == kwargs["name"]:
                app_logger.debug(f'{kwargs["name"]} already exists with google_id: {file_data.id}')
                return CreateDirectoryResults(should_insert=False,
                                              directoryTreeObj=DirectoryTreeModel.find_by_google_id(file_data.id))
        new_id = GoogleDriveCommands.create_directory(parent_directory_id=kwargs["google_id"],
                                                      directory_name=kwargs["name"])
        kwargs["google_id"] = new_id
        return DirectoryCreator.create_directory_model(**kwargs)

    @staticmethod
    def create_directory_model(**kwargs):
        if not kwargs["google_id"]:
            raise ValueError(f'Directory {kwargs["name"]} not created, no google_id received')
        directory = DirectoryTreeModel(**kwargs)
        app_logger.debug(f"Directory to be saved {directory}")
        return CreateDirectoryResults(should_insert=True, directoryTreeObj=directory)
