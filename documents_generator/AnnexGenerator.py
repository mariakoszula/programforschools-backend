from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.date_converter import DateConverter
from helpers.file_folder_creator import DirectoryCreator
from helpers.config_parser import config_parser
from helpers.common import get_output_name
from os import path


class AnnexGenerator(DocumentGenerator):
    def prepare_data(self):
        self._document.merge(
            city=self.annex.contract.school.city,
            current_date=self.date,
            contract_no=self.annex.contract.contract_no.split(" ")[-1],
            contract_year=self.annex.contract.contract_year,
            semester_no=self.annex.contract.program.get_current_semester(),
            school_year=self.annex.contract.program.school_year,
            name=self.annex.contract.school.name,
            address=self.annex.contract.school.address,
            nip=self.annex.contract.school.nip,
            regon=self.annex.contract.school.regon,
            responsible_person=self.annex.contract.school.fill_responsible_person(),
            fruitveg_products=self.annex.fruitVeg_products,
            dairy_products=self.annex.dairy_products,
            validity_date=DateConverter.convert_date_to_string(self.annex.validity_date),
            annex_no=self.annex.no,
            validity_date_end="-"
        )

    def __init__(self, annex, date):
        self.date = date
        self.annex = annex
        program_dir = DirectoryCreator.get_main_dir(school_year=self.annex.contract.program.school_year,
                                                    semester_no=self.annex.contract.program.semester_no)

        _template_document = config_parser.get('DocTemplates', 'annex')
        _output_directory = path.join(program_dir,
                                      config_parser.get('Directories', 'annex'))
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'annex'),
                                   output_directory=path.join(program_dir,
                                                              config_parser.get('Directories', 'annex')),
                                   output_name=get_output_name('annex',
                                                               self.annex.contract.school.nick.strip(),
                                                               self.annex.contract.contract_no,
                                                               self.annex.contract.contract_year,
                                                               self.annex.no))
