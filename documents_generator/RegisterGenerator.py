from datetime import datetime
from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.config_parser import config_parser
from models.program import ProgramModel
from helpers.file_folder_creator import DirectoryCreator


class RegisterGenerator(DocumentGenerator):
    def prepare_data(self):
        self._document.merge(
            semester_no="1")

    def __init__(self, program: ProgramModel):
        self.date = datetime.today().strftime('%d-%m-%Y')
        self.program = program
        DocumentGenerator.__init__(self,
                                   config_parser.get('DocTemplates', 'register'),
                                   DirectoryCreator.get_main_dir(school_year=self.program.school_year,
                                                                 semester_no=self.program.semester_no),
                                   config_parser.get('DocNames', 'register').format(self.date))
