from datetime import datetime
from documents_generator.DocumentGenerator import DocumentGenerator
from config_parser import config_parser


class RegisterGenerator(DocumentGenerator):
    def prepare_data(self):
        self._document.merge(
            semester_no="1")

    def __init__(self, program_id):
        self.date = datetime.today().strftime('%d-%m-%Y')

        DocumentGenerator.__init__(self,
                                   config_parser.get('DocTemplates', 'register'),
                                   DocumentGenerator.get_output_dir(program_id),
                                   config_parser.get('DocNames', 'register').format(self.date))
