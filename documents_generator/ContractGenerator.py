from helpers.common import EMPTY_FILED
from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.date_converter import DateConverter
from helpers.file_folder_creator import DirectoryCreator
from models.contracts import ContractModel
from helpers.config_parser import config_parser
from os import path


class ContractGenerator(DocumentGenerator):
    def prepare_data(self):
        self._document.merge(
            city=self.contract.school.city,
            date=self.date,
            no=str(self.contract.contract_no),
            year=str(self.contract.contract_year),
            semester=self.contract.program.get_current_semester(),
            name=self.contract.school.name,
            address=self.contract.school.address,
            nip=self.contract.school.nip,
            regon=self.contract.school.regon,
            representant=EMPTY_FILED if self.omit_representative else self.contract.school.fill_responsible_person(),
            email=self.contract.school.email,
            program_start_date=DateConverter.convert_date_to_string(self.contract.program.start_date),
            program_end_date=DateConverter.convert_date_to_string(self.contract.program.end_date),
            nip_additional=self.contract.school.representative_nip if self.contract.school.representative_nip else "-",
            name_additional=self.contract.school.representative if self.contract.school.representative else "-",
            regon_additional=self.contract.school.representative_regon if self.contract.school.representative_regon else "-",
            giving_weeks=ContractGenerator._prepare_str_from_weeks(self.contract.program.weeks))

    def __init__(self, contract: ContractModel, date, omit_representative=False, empty=False):
        self.contract = contract
        self.omit_representative = omit_representative
        self.date = date
        program_dir = DirectoryCreator.get_main_dir(school_year=self.contract.program.school_year,
                                                    semester_no=self.contract.program.semester_no)
        doc_template = config_parser.get('DocTemplates', 'contract') if not empty else config_parser.get('DocTemplates',
                                                                                                         'contract_empty')
        DocumentGenerator.__init__(self,
                                   template_document=path.join(config_parser.get('DocTemplates', 'directory'),
                                                               DirectoryCreator.get_part_with_year_and_sem(
                                                                   school_year=self.contract.program.school_year,
                                                                   semester_no=self.contract.program.semester_no),
                                                               doc_template),
                                   output_directory=path.join(program_dir,
                                                              config_parser.get('Directories', 'contract')),
                                   output_name=config_parser.get('DocNames', 'contract').format(
                                       self.contract.school.nick.strip(),
                                       self.contract.contract_no,
                                       self.contract.contract_year))

    @staticmethod
    def _prepare_str_from_weeks(weeks):
        return ",".join(["{0}-{1}".format(DateConverter.convert_date_to_string(week.start_date, "%d.%m"),
                                          DateConverter.convert_date_to_string(week.end_date)) for week in weeks])
