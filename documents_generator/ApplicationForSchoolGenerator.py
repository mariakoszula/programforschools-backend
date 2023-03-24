from documents_generator.ApplicationGenerator import template_postfix, get_application_dir
from documents_generator.DocumentGenerator import DocumentGenerator
from typing import Dict, List
from collections import defaultdict
from helpers.common import get_template
from helpers.date_converter import DateConverter
from helpers.google_drive import GoogleDriveCommands
from models.application import ApplicationModel, ApplicationType
from models.contract import ContractModel
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
        self._prepare()

    def _prepare(self):
        raise NotImplementedError

    def get(self):
        return self.data


class DefaultData(DataContainer):
    def __init__(self, school: SchoolModel, sign_date):
        self.school = school
        self.sign_date = DateConverter.convert_to_date(sign_date)
        super().__init__()

    def _prepare(self):
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


WEEK_TEMPLATE = "week"
KIDS_NO_TEMPLATE = "kids_no"
PORTION_TEMPLATE = "portion"


class StatementsBaseData(DataContainer):
    def _prepare(self):
        self.data.update(self.default_data.get())
        self.data["application_no"] = str(self.application)
        self.__fill_if_last_application()
        self.__prepare_per_week(WEEK_TEMPLATE, lambda week: week.str_for_docs())
        self.__prepare_per_week(KIDS_NO_TEMPLATE, lambda week: max(
            record.delivered_kids_no for record in self.records if record.week == week))
        self.__prepare_per_week(PORTION_TEMPLATE,
                                lambda week: len([record for record in self.records if record.week == week]))
        self.data["kids_no"] = self.__max_kids()

    def __init__(self, application: ApplicationModel, date, records: List[RecordModel], start_week: int,
                 is_last: bool = False, _output_dir=None):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        if start_week < 1 or start_week > 14:
            raise ValueError("Start week must be between 1 and 14")
        school: SchoolModel = records[0].contract.school
        self.records = records
        self.contract: ContractModel = records[0].contract
        self.default_data = DefaultData(school, date)
        self.output_name = config_parser.get('DocNames', 'records_statements').format(school.nick.strip())
        self.is_last = is_last
        self.template_doc = get_template(application.program,
                                         config_parser.get('DocTemplates', 'records_statements').format(
                                             template_postfix(application.type)))
        self.output_dir = get_application_dir_per_school(application) if _output_dir is None else _output_dir
        self.application = application
        self.start_week = start_week
        super().__init__()

    def __fill_if_last_application(self):
        self.data["l"] = "X" if self.is_last else ""
        self.data["p"] = "X" if not self.is_last else ""

    def __max_kids(self):
        max_kids = self.contract.fruitVeg_products if \
            self.application.type == ApplicationType.FRUIT_VEG else self.contract.dairy_products
        assert max_kids > 0 and "Maximum number of kids must be greater than 0"
        for key, val in self.data.items():
            if key.startswith("kids_no"):
                if val > max_kids:
                    max_kids = val
        return max_kids

    def __prepare_per_week(self, base_name, fun):
        for no, week in enumerate(self.application.weeks, start=self.start_week):
            self.data[f"{base_name}_{no}"] = fun(WeekModel.find_by_id(week.id))


class StatementGenerator(DocumentGenerator):
    def prepare_data(self):
        data_to_merge = dict()
        data_to_merge.update(self.bd.get())
        data_to_merge.update(**self.product_dict)
        data_to_merge.update(**self.__products_with_zero(data_to_merge))
        self.merge(**data_to_merge)

    def __init__(self, baseData: StatementsBaseData, _drive_tool=GoogleDriveCommands):
        self.bd = baseData
        self.product_dict = defaultdict(int)
        self.__fill_product_data()
        DocumentGenerator.__init__(self,
                                   template_document=self.bd.template_doc,
                                   output_directory=self.bd.output_dir,
                                   output_name=self.bd.output_name,
                                   drive_tool=_drive_tool)

    def __products_with_zero(self, data_to_merge):
        res = dict()
        keys_in_template = set(self.get_missing_keys())
        keys_in_mege = set(data_to_merge.keys())
        for key in keys_in_template.difference(keys_in_mege):
            if WEEK_TEMPLATE in key or PORTION_TEMPLATE in key or KIDS_NO_TEMPLATE in key:
                res[key] = "-"
            else:
                res[key] = "0"
        return res

    def __fill_product_data(self):
        for record in self.bd.records:
            template_name = record.product_store.product.template_name
            sum_template_name = record.product_store.product.type.template_name()
            self.product_dict.setdefault(f"{template_name}", 0)
            self.product_dict[f"{template_name}"] += record.delivered_kids_no
            self.product_dict.setdefault(f"{sum_template_name}", 0)
            self.product_dict[f"{sum_template_name}"] += record.delivered_kids_no


def statement_factory(application: ApplicationModel, records: List[RecordModel], date, start_week: int,
                      is_last: bool = False, _output_dir=None, _drive_tool=GoogleDriveCommands):
    sbd = StatementsBaseData(application, date, records, start_week, is_last, _output_dir)
    return StatementGenerator(sbd, _drive_tool=_drive_tool)
