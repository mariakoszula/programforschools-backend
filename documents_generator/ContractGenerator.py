from helpers.common import EMPTY_FILED, get_output_name
from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.date_converter import DateConverter
from models.contract import ContractModel
from helpers.config_parser import config_parser
from os import path

from models.week import WeekModel


class ContractGenerator(DocumentGenerator):
    def prepare_data(self):
        self.merge(
            city=self.contract.school.city,
            date=self.date,
            no=self.contract.contract_no,
            year=self.contract.contract_year,
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
            giving_weeks=WeekModel.prepare_str_from_weeks(self.contract.program.weeks))

    def __init__(self, contract: ContractModel, date, omit_representative=True, empty=False):
        self.contract = contract
        self.omit_representative = omit_representative
        self.date = date
        program_dir = self.contract.program.get_main_dir()
        doc_template = config_parser.get('DocTemplates', 'contract') if not empty else config_parser.get('DocTemplates',
                                                                                                         'contract_empty')
        DocumentGenerator.__init__(self,
                                   template_document=self.__get_template(doc_template),
                                   output_directory=path.join(program_dir,
                                                              config_parser.get('Directories', 'contract')),
                                   output_name=get_output_name('contract',
                                                               self.contract.school.nick.strip(),
                                                               self.contract.contract_no,
                                                               self.contract.contract_year))

    def __get_template(self, doc_template):
        return path.join(config_parser.get('DocTemplates', 'directory'),
                         self.contract.program.get_part_with_year_and_sem(),
                         doc_template)
