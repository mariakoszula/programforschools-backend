from documents_generator.ApplicationGenerator import template_postfix, get_application_dir
from documents_generator.DocumentGenerator import DocumentGenerator
from typing import Dict, List

from helpers.common import get_template
from helpers.date_converter import DateConverter
from helpers.google_drive import GoogleDriveCommands
from models.application import ApplicationModel
from models.record import RecordModel
from models.school import SchoolModel
from helpers.config_parser import config_parser
from os import path

from models.week import WeekModel


def get_application_dir_per_school(application: ApplicationModel):
    return path.join(get_application_dir(application), config_parser.get('Directories', 'applicationForSchool'))


class DataContainer(object):
    def __init__(self):
        self.data: Dict = dict()

    def prepare(self):
        raise NotImplementedError

    def get(self):
        return self.data


class DefaultData(DataContainer):
    def __init__(self, school: SchoolModel, sign_date):
        super().__init__()
        self.school = school
        self.sign_date = DateConverter.convert_to_date(sign_date)

    def prepare(self):
        self.data['school_name'] = self.school.name
        self.data['school_nip'] = self.school.nip
        self.data['school_regon'] = self.school.regon
        self.data['school_address'] = self.school.address
        self.data['city'] = self.school.city
        self.data['date_day'] = DateConverter.two_digits(self.sign_date.day)
        self.data['date_month'] = DateConverter.two_digits(self.sign_date.month)
        self.data['date_year'] = self.sign_date.year


class RecordsSummaryGenerator(DocumentGenerator):
    def prepare_data(self):
        self.default_data.prepare()
        data_to_merge = dict()
        data_to_merge.update(self.default_data.get())
        data_to_merge['weeks'] = WeekModel.prepare_str_from_weeks(self.application.program.weeks)

        self.merge_rows('record_date', self.__record_date_info())
        data_to_merge['product_sum'] = self.product_sum
        self.merge(**data_to_merge)

    def __init__(self, application: ApplicationModel, records: List[RecordModel], date, _output_dir=None,
                 _drive_tool=GoogleDriveCommands):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        school: SchoolModel = records[0].contract.school
        self.records = records
        self.application = application
        self.default_data = DefaultData(school, date)
        self.product_sum = sum([record.delivered_kids_no for record in self.records])
        _template_doc = config_parser.get('DocTemplates', 'records_summary').format(template_postfix(application.type))
        if _output_dir is None:
            _output_dir = get_application_dir_per_school(application)

        _output_name = config_parser.get('DocNames', 'records_summary').format(school.nick.strip())
        DocumentGenerator.__init__(self,
                                   template_document=get_template(application.program, _template_doc),
                                   output_directory=_output_dir,
                                   output_name=_output_name,
                                   drive_tool=_drive_tool)

    def __record_date_info(self):
        records = []
        for record in self.records:
            records.append({
                "record_date": DateConverter.convert_date_to_string(record.date),
                "kids": record.delivered_kids_no,
                "product": record.product_store.product.name,
            })
        return records


class StatementsDiaryGenerator(DocumentGenerator):
    def prepare_data(self):
        pass

    def __init__(self, application: ApplicationModel, records: List[RecordModel], date):
        if not len(records):
            raise ValueError("List with records cannot be empty")


# TODO for FULL application support
class StatementsGenerator(DocumentGenerator):
    def prepare_data(self):
        pass
