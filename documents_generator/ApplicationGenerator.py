from app import create_app
from helpers.common import DOCX_MIME_TYPE
from models.product import ProductTypeModel, ProductModel
from helpers.config_parser import config_parser
from documents_generator.DocumentGenerator import DocumentGenerator
from typing import Dict, List
from collections import defaultdict

from helpers.date_converter import DateConverter
from helpers.google_drive import GoogleDriveCommands
from models.application import ApplicationModel, ApplicationType
from models.contract import ContractModel
from models.record import RecordModel, RecordState
from models.school import SchoolModel
from models.week import WeekModel
from decimal import ROUND_HALF_UP, getcontext, Decimal
from collections import namedtuple
from os import path

getcontext().rounding = ROUND_HALF_UP
round_number = Decimal('.01')


def _get_template(program, doc_template):
    return path.join(config_parser.get('DocTemplates', 'directory'),
                     program.get_part_with_year_and_sem(),
                     doc_template)


def template_postfix(name):
    if name == ApplicationType.FULL:
        return f""
    return f"_{ProductTypeModel.dairy_name(replace=True) if name == ApplicationType.DAIRY else ProductTypeModel.fruit_veg_name()}"


def get_application_dir_per_school(application: ApplicationModel):
    return path.join(get_application_dir(application), config_parser.get('Directories', 'applicationForSchool'))


def get_application_dir(application: ApplicationModel):
    program_dir = application.program.get_main_dir()
    return path.join(program_dir, application.get_dir())


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


class ApplicationCommonData:
    @staticmethod
    def add_weeks(data: Dict, application: ApplicationModel):
        data['weeks'] = WeekModel.prepare_str_from_weeks(application.weeks)

    @staticmethod
    def add_application_no(data: Dict, application: ApplicationModel):
        data["application_no"] = str(application)

    @staticmethod
    def add_is_last(data: Dict, is_last: bool):
        data["l"] = "X" if is_last else ""
        data["p"] = "X" if not is_last else ""


class RecordsSummaryGenerator(DocumentGenerator):
    def prepare_data(self):
        self.data.update(self.default_data.get())
        ApplicationCommonData.add_weeks(self.data, self.application)
        self.merge_rows('record_date', self.__record_date_info())
        self.merge(**self.data)

    def __init__(self, application: ApplicationModel, records: List[RecordModel], date, _output_dir=None,
                 _drive_tool=GoogleDriveCommands):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        school: SchoolModel = records[0].contract.school
        self.records = records
        self.application = application
        self.default_data = DefaultData(school, date)
        self.data = dict()
        self.data['product_sum'] = sum([record.delivered_kids_no for record in self.records])

        _template_doc = config_parser.get('DocTemplates', 'records_summary').format(
            template_postfix(application.type))
        if _output_dir is None:
            _output_dir = get_application_dir_per_school(application)

        _output_name = config_parser.get('DocNames', 'records_summary').format(school.nick.strip())
        DocumentGenerator.__init__(self,
                                   template_document=_get_template(application.program, _template_doc),
                                   output_directory=_output_dir,
                                   output_name=_output_name,
                                   drive_tool=_drive_tool)
        self.change_mime_type(DOCX_MIME_TYPE)

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
        ApplicationCommonData.add_application_no(self.data, self.application)
        ApplicationCommonData.add_is_last(self.data, self.is_last)
        self.__prepare_per_week(WEEK_TEMPLATE, lambda week: week.str_for_docs())
        self.__prepare_per_week(KIDS_NO_TEMPLATE, lambda week: max(
            record.delivered_kids_no for record in self.records if record.week == week))
        self.__prepare_per_week(PORTION_TEMPLATE,
                                lambda week: len([record for record in self.records if record.week == week]))
        self.maximum_kids_no = self.__max_kids()
        self.data["kids_no"] = self.__max_kids(init_value=self.__kids_on_contract())

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
        self.maximum_kids_no = 0
        self.template_doc = _get_template(application.program,
                                          config_parser.get('DocTemplates', 'records_statements').format(
                                              template_postfix(application.type)))
        self.output_dir = get_application_dir_per_school(application) if _output_dir is None else _output_dir
        self.application = application
        self.start_week = start_week
        super().__init__()

    def __kids_on_contract(self):
        max_kids = self.contract.fruitVeg_products if \
            self.application.type == ApplicationType.FRUIT_VEG else self.contract.dairy_products
        assert max_kids > 0 and "Maximum number of kids must be greater than 0"
        return max_kids

    def __max_kids(self, init_value=0):
        max_kids = init_value
        for key, val in self.data.items():
            if key.startswith("kids_no"):
                if val > max_kids:
                    max_kids = val
        return max_kids

    def __prepare_per_week(self, base_name, fun):
        for no, week in enumerate(self.application.weeks, start=self.start_week):
            self.data[f"{base_name}_{no}"] = fun(WeekModel.find_by_id(week.id))


def fill_product_data(records: List[RecordModel], product_dict: defaultdict):
    for record in records:
        template_name = record.product_store.product.template_name
        sum_template_name = record.product_store.product.type.template_name()
        product_dict.setdefault(f"{template_name}", 0)
        product_dict[f"{template_name}"] += record.delivered_kids_no
        product_dict.setdefault(f"{sum_template_name}", 0)
        product_dict[f"{sum_template_name}"] += record.delivered_kids_no


class StatementGenerator(DocumentGenerator):
    def prepare_data(self):
        self.data.update(self.bd.get())
        self.data.update(**self.product_dict)
        self.data.update(**self.__products_with_zero())
        self.merge(**self.data)

    def __init__(self, baseData: StatementsBaseData, _drive_tool=GoogleDriveCommands):
        self.bd = baseData
        self.product_dict = defaultdict(int)
        self.data = dict()
        fill_product_data(self.bd.records, self.product_dict)
        DocumentGenerator.__init__(self,
                                   template_document=self.bd.template_doc,
                                   output_directory=self.bd.output_dir,
                                   output_name=self.bd.output_name,
                                   drive_tool=_drive_tool)
        self.change_mime_type(DOCX_MIME_TYPE)

    def __products_with_zero(self):
        res = dict()
        for key in self.get_missing_keys(self.data):
            if WEEK_TEMPLATE in key or PORTION_TEMPLATE in key or KIDS_NO_TEMPLATE in key:
                res[key] = "-"
            else:
                res[key] = "0"
        return res


def statement_factory(application: ApplicationModel, records: List[RecordModel], date, start_week: int,
                      is_last: bool = False, _output_dir=None, _drive_tool=GoogleDriveCommands):
    sbd = StatementsBaseData(application, date, records, start_week, is_last, _output_dir)
    return StatementGenerator(sbd, _drive_tool=_drive_tool)


InconsistencyError = namedtuple("InconsistencyError", ["school", "message"])


class KidsInconsistencyError:
    def __init__(self, record: RecordModel, expected_kids_no):
        self.record = record
        self.expected_kids_no = expected_kids_no

    def __str__(self):
        return f"{DateConverter.convert_date_to_string(self.record.date)}: {self.record} -> {self.expected_kids_no}"


class StateInconsistencyError:
    def __init__(self, record: RecordModel):
        self.record = record

    def __str__(self):
        return f"{DateConverter.convert_date_to_string(self.record.date)}: {self.record} != RecordState.DELIVERED"


class WeekInconsistencyError:
    def __init__(self, week: WeekModel):
        self.week = week

    def __str__(self):
        return f"{self.week}"


class ApplicationGenerator(DocumentGenerator):

    @staticmethod
    def check_record_consistency(application: ApplicationModel):
        errors: List[InconsistencyError] = []
        for contract in application.contracts:
            records = ApplicationGenerator.__get_records_all(application, contract)
            for record in records:
                ApplicationGenerator.__check_kids_inconsistency(contract, errors, record)
                ApplicationGenerator.__check_state_inconsistency(contract, errors, record)
            ApplicationGenerator.__check_week_inconsistency(contract, errors, records, application.weeks)
        return errors

    @staticmethod
    def __get_records_all(application: ApplicationModel, contract):
        records = RecordModel.filter_records_by_contract(application, contract)
        records.extend(RecordModel.filter_records_by_contract(application, contract, state=RecordState.PLANNED))
        records.extend(RecordModel.filter_records_by_contract(application, contract, state=RecordState.GENERATED))
        records.extend(
            RecordModel.filter_records_by_contract(application, contract, state=RecordState.GENERATION_IN_PROGRESS))
        return records

    @staticmethod
    def __check_state_inconsistency(contract, errors, record):
        if record.state != RecordState.DELIVERED:
            errors.append(InconsistencyError(contract.school,
                                             StateInconsistencyError(record)))

    @staticmethod
    def __check_kids_inconsistency(contract, errors, record):
        expected = record.contract.get_kids_no(product_type=record.product_store.product.type,
                                               date=record.date)
        if record.delivered_kids_no is not None and record.delivered_kids_no != expected:
            errors.append(InconsistencyError(contract.school,
                                             KidsInconsistencyError(record, expected)))

    @staticmethod
    def __check_week_inconsistency(contract, errors, records, weeks):
        for week in weeks:
            if not any(filter(lambda r: r.week_id == week.id, records)):
                errors.append(InconsistencyError(contract.school,
                                                 WeekInconsistencyError(week)))

    def prepare_data(self):
        ApplicationCommonData.add_application_no(self.data, self.application)
        ApplicationCommonData.add_weeks(self.data, self.application)
        ApplicationCommonData.add_is_last(self.data, self.is_last)
        self.data["app_school_no"] = len(self.application.contracts)
        self.data["weeks_no"] = len(self.application.weeks)
        self.data["kids_no"] = sum([s.bd.maximum_kids_no for s in self.statements])
        self.__fill_product_details()
        self.__fill_income()
        self.data.update(**self.__products_with_zero())
        self.merge(**self.data)

    def validate_statements_with_application(self):
        for product_key, amount in self.product_dict.items():
            statements_amount = sum([statement.product_dict[product_key] for statement in self.statements])
            if amount != statements_amount:
                raise ValueError(
                    f"Amount of {product_key} in statements <{statements_amount}> is "
                    f"not equal to amount in application <{amount}>")

    def __init__(self, application: ApplicationModel,
                 records_summary: List[RecordsSummaryGenerator],
                 statements: List[StatementGenerator], is_last: bool = False,
                 _output_dir=None, _drive_tool=GoogleDriveCommands):
        if not len(statements):
            raise ValueError("List with statements cannot be empty")
        self.application = application
        self.statements = statements
        self.records_summary = records_summary
        self.is_last = is_last
        self.records = RecordModel.filter_records(application)
        self.product_dict = defaultdict(int)
        self.data = dict()
        fill_product_data(self.records, self.product_dict)
        self.validate_statements_with_application()
        _template_doc = config_parser.get('DocTemplates', 'application').format(
            template_postfix(application.type))
        if _output_dir is None:
            _output_dir = get_application_dir(application)

        _output_name = config_parser.get('DocNames', 'application').format(self.application.get_str_name())
        DocumentGenerator.__init__(self,
                                   template_document=_get_template(application.program, _template_doc),
                                   output_directory=_output_dir,
                                   output_name=_output_name,
                                   drive_tool=_drive_tool)
        self.change_mime_type(DOCX_MIME_TYPE)

    def __products_with_zero(self):
        res = dict()
        for key in self.get_missing_keys(self.data):
            res[key] = "0"
        return res

    def __product_price(self, product: ProductModel):
        if product.type.name == ProductTypeModel.DAIRY_TYPE:
            return Decimal(self.application.program.dairy_price)
        else:
            return Decimal(self.application.program.fruitVeg_price)

    def __fill_product_details(self):
        with create_app().app_context():
            for name, amount in self.product_dict.items():
                if "all" not in name:
                    product = ProductModel.find_by(template_name=name)
                    amount = Decimal(amount)
                    all_name = product.type.template_name()
                    self.__fill_product(all_name, name, amount)
                    self.__fill_product(all_name, name, amount * self.__product_price(product), postfix="wn")
                    self.__fill_product(all_name, name, self.data[f"{name}wn"] * Decimal(product.vat) / 100,
                                        postfix="vat")
                    self.__fill_product(all_name, name, self.data[f"{name}wn"] + self.data[f"{name}vat"], postfix="wb")
            for name, amount in self.data.items():
                if "wn" in name or "vat" in name or "wb" in name:
                    self.data[name] = f"{amount:.2f}"

    def __fill_product(self, all_name, name, amount, postfix=""):
        all_key = f"{all_name}{postfix}"
        key = f"{name}{postfix}"
        self.data[key] = amount
        self.data[all_key] = self.data.get(all_key, 0) + amount

    def __fill_income(self):
        income = 0
        for name, amount in self.data.items():
            if "allwb" in name:
                income += Decimal(amount)
        self.data["income"] = f"{income:.2f}"


def application_factory(application: ApplicationModel, date, start_week, is_last: bool = False,
                        _output_dir=None, _drive_tool=GoogleDriveCommands):
    records_summary = []
    statements = []
    try:
        for contract in application.contracts:
            records = RecordModel.filter_records_by_contract(application, contract)
            records_summary.append(
                RecordsSummaryGenerator(application, records, date, _output_dir=_output_dir, _drive_tool=_drive_tool))
            statements.append(statement_factory(application, records, date, start_week, _output_dir=_output_dir,
                                                _drive_tool=_drive_tool))
    except ValueError as e:
        raise ValueError(f"Error while creating application for {application.get_str_name()}: {e}")
    return ApplicationGenerator(application, records_summary, statements, is_last, _output_dir, _drive_tool)
