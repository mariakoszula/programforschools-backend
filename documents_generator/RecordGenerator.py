from os import path

from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.common import get_output_name
from helpers.config_parser import config_parser
from helpers.file_folder_creator import DirectoryCreator
from helpers.date_converter import DateConverter
from models.product import ProductTypeModel
from models.record import RecordModel


def get_record_title_mapping(product_type: ProductTypeModel):
    if product_type.is_dairy():
        return "Mleko i przetwory mleczne"
    if product_type.is_fruit_veg():
        return "Warzywa i owoce "


class RecordGenerator(DocumentGenerator):
    @staticmethod
    def get_record_output_name(record: RecordModel):
        return get_output_name('record', f"{record.contract.school.nick.strip()}",
                               DateConverter.convert_date_to_string(record.date, pattern="%Y-%m-%d"),
                               record.product_store.product.type.name[:3])

    def prepare_data(self):
        self._document.merge(**RecordGenerator.prepare_data_to_fill(self.record))

    def __init__(self, record: RecordModel):
        self.record = record
        program_dir = DirectoryCreator.get_main_dir(school_year=self.record.contract.program.school_year,
                                                    semester_no=self.record.contract.program.semester_no)
        DocumentGenerator.__init__(self,
                                   template_document=RecordGenerator.get_template(),
                                   output_directory=path.join(program_dir,
                                                              config_parser.get('Directories', 'school'),
                                                              self.record.contract.school.nick,
                                                              config_parser.get('Directories', 'record')),
                                   output_name=self.get_record_output_name(self.record))

    @staticmethod
    def prepare_data_to_fill(record):
        return {
            'city': record.contract.school.city,
            'current_date': DateConverter.convert_date_to_string(record.date),
            'name': record.contract.school.name,
            'address': record.contract.school.address,
            'nip': record.contract.school.nip,
            'regon': record.contract.school.regon,
            'email': record.contract.school.email,
            'kids_no': record.delivered_kids_no,
            'product_name': record.product_store.product.name,
            'record_title': get_record_title_mapping(record.product_store.product.type)
        }

    @staticmethod
    def get_template():
        return config_parser.get('DocTemplates', 'record')
