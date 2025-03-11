from datetime import datetime

from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.date_converter import DateConverter
from helpers.google_drive import GoogleDriveCommands
from models.application import ApplicationModel
from models.product import ProductTypeModel
from models.program import ProgramModel
from helpers.config_parser import config_parser
from helpers.common import get_output_name
from models.record import RecordModel, RecordState
from app import create_app

class RecordRegisterGenerator(DocumentGenerator):
    def __prepare_record_data(self, record: RecordModel, component_type: str):
        data = dict()
        data['no'] = record.get_record_no()
        data['date'] = DateConverter.convert_date_to_string(record.date)
        data['school_name'] = record.contract.school.name
        data['component'] = component_type
        app_key = (record.contract_id, record.week_id)
        data['application'] = '-' if app_key not in self.applications else f"{self.applications[app_key]}"
        return data

    def prepare_data(self):
        with create_app().app_context():
            rows = []
            sorted_records = sorted(self.record_by_school_and_product.items())
            for contract_component, records in sorted_records:
                _, component = contract_component
                for record in records:
                    rows.append(self.__prepare_record_data(record, component))
            self.merge_rows('no', rows)
            self.merge(
                date=self.date,
                semester_no=self.program.get_current_semester(),
                school_year=self.program.school_year
            )

    def __init__(self, program: ProgramModel, _output_dir=None, _drive_tool=GoogleDriveCommands):
        self.program = program
        self.date = datetime.today().strftime('%d-%m-%Y')
        records = RecordModel.all_filtered_by_program(self.program.id).order_by(RecordModel.date)
        self.applications = { (contract.id, week.id): app for app in ApplicationModel.all_filtered_by_program(self.program.id) for week in app.weeks for contract in app.contracts}
        self.record_by_school_and_product: dict[tuple[int, str], list[RecordModel]] = {}

        for record in records:
            product_type = ProductTypeModel.find_by_id(record.product_type_id)
            key = (record.contract_id, ProductTypeModel.DAIRY_TYPE) if product_type.is_dairy() else (record.contract_id, f"{ProductTypeModel.VEGETABLE_TYPE }-{ProductTypeModel.FRUIT_TYPE}")
            if key not in self.record_by_school_and_product:
                self.record_by_school_and_product[key] = list()
            if record.state in (RecordState.GENERATED, RecordState.DELIVERED):
                self.record_by_school_and_product[key].append(record)

        if _output_dir is None:
            _output_dir = self.program.get_main_dir()

        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'record_register'),
                                   output_directory=_output_dir,
                                   output_name=get_output_name('record_register', self.date),
                                   drive_tool=_drive_tool)