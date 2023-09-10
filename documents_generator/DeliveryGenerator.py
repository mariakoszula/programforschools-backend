from os import path
from typing import List

from documents_generator.DocumentGenerator import DocumentGenerator
from documents_generator.RecordGenerator import RecordGenerator
from helpers.common import get_output_name
from helpers.config_parser import config_parser
from helpers.date_converter import DateConverter
from models.product import  ProductStoreModel
from models.record import RecordModel
from models.week import WeekModel
from helpers.logger import app_logger


class SummaryRecords:
    def __init__(self, records: List[RecordModel], add_weights):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        self.records = records
        self.add_weights = add_weights
        self.product_summarize_rows = []

    def prepare_data(self):
        self._product_summarize_info()

    @staticmethod
    def __sum_products(records):
        _sum = 0
        for r in records:
            if not r.delivered_kids_no:
                app_logger.error(f"Record does not have delivered_kids_no: {r}")
                continue
            _sum += r.delivered_kids_no
        return _sum

    @staticmethod
    def dict_from_list(data, get_key_fun):
        new_dict = {}
        for record in data:
            res = new_dict.get(get_key_fun(record), None)
            if res:
                res.append(record)
            else:
                new_dict[get_key_fun(record)] = [record]
        return new_dict

    def _product_summarize_info(self):
        for product_store, records in SummaryRecords.dict_from_list(self.records,
                                                                    lambda record: record.product_store).items():
            self.product_summarize_rows.append(self._prepare_product_summarize(product_store, records))

    def _prepare_product_summarize(self, product_store: ProductStoreModel, records: List[RecordModel]):
        product_amount = SummaryRecords.__sum_products(records)
        if self.add_weights:
            weight = f"{product_amount * product_store.weight:.2f} {product_store.product.weight.name}"
            product_amount = f" {product_amount} [{weight}]"
        base = {
            "product": product_store.product.name,
            "products_sum": f"{product_amount}"}
        return base


def get_output_dir(record, delivery_date):
    return path.join(get_main_output_dir(record), delivery_date)


def get_main_output_dir(record):
    program_dir = record.contract.program.get_main_dir()
    return path.join(program_dir, config_parser.get('Directories', 'record'))


class DeliveryGenerator(SummaryRecords, DocumentGenerator):
    DAY_NAMES = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"]

    def _school_product_summarize(self, nick):
        records = filter(lambda record: record.contract.school.nick == nick, self.records)
        results = []
        for product, records in SummaryRecords.dict_from_list(records,
                                                              lambda record: record.product_store.product.name).items():
            results.append(f"{product}")
        return ", ".join(results)

    @staticmethod
    def _prepare_records_with_product(records: List[RecordModel]):
        return " + ".join([f"{str(record)}" for record in records])

    def _prepare_school_delivery(self, school_nick: str, records: List[RecordModel]):
        return {
            "school_nick": school_nick,
            "records_with_products": self._prepare_records_with_product(records),
            "box_with_products_for_school": self._school_product_summarize(school_nick)
        }

    def _schools_delivery_info(self):
        for nick, records in SummaryRecords.dict_from_list(self.records, lambda record: record.contract.school.nick).items():
            self.schools_delivery_rows.append(self._prepare_school_delivery(nick, records))

    @staticmethod
    def get_delivery_output_name(tmpl_name, delivery_date, driver):
        return get_output_name(tmpl_name, delivery_date, f"Kierowca_{driver}" if driver else DeliveryGenerator.DAY_NAMES[DateConverter.get_day(delivery_date)])

    def prepare_data(self):
        super().prepare_data()
        self._schools_delivery_info()
        self.merge_rows("school_nick", self.schools_delivery_rows)
        self.merge_rows("product", self.product_summarize_rows)
        self.merge(
            driver=self.driver.upper() if self.driver else f"Rozpiska",
            delivery_date=self.delivery_date,
            delivery_day=DeliveryGenerator.DAY_NAMES[DateConverter.get_day(self.delivery_date)].upper(),
            comments=self.comments
        )

    def __init__(self, records: List[RecordModel], date, driver=None, comments=None):
        super().__init__(records, add_weights=not driver)
        self.schools_delivery_rows = []
        self.delivery_date = date
        self.driver = driver
        self.comments = comments
        self.records = records
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'delivery'),
                                   output_directory=get_output_dir(self.records[0], self.delivery_date),
                                   output_name=DeliveryGenerator.get_delivery_output_name('delivery', self.delivery_date, self.driver))


class DeliveryRecordsGenerator(DocumentGenerator):
    def prepare_data(self):
        self.merge_pages([RecordGenerator.prepare_data_to_fill(record) for record in self.records])

    def __init__(self, records, date, driver, **_):
        self.records = records
        output_directory = get_output_dir(self.records[0], date)
        DocumentGenerator.__init__(self,
                                   template_document=RecordGenerator.get_template(),
                                   output_directory=output_directory,
                                   output_name=DeliveryGenerator.get_delivery_output_name('record_all', date, driver))


def mf_product(_day, _type):
    return f"{_type}_{_day}"


FRUIT = "fruit"
DAIRY = "dairy"


def prepare_product_dict(_type, records):
    d = {}
    max_width = 0
    for r in records:
        day_no = DateConverter.get_day(r.date)
        key = mf_product(SummaryGenerator.DAY_NAMES[day_no - 1], _type)
        if max_width < len(str(r)):
            max_width = len(str(r))
        d[key] = f"{r}"
    for day in SummaryGenerator.DAY_NAMES:
        key = mf_product(day, _type)
        if key not in d:
            d[key] = f""
        d[key] = d[key].ljust(max_width)
    return d


class SummaryGenerator(SummaryRecords, DocumentGenerator):
    DAY_NAMES = ["mon", "tue", "wed", "th", "fri"]

    def prepare_data(self):
        super().prepare_data()
        self.merge_rows("product", self.product_summarize_rows)
        self.merge(week_dates=self.week)

    def __init__(self, records: List[RecordModel]):
        if len(records) == 0:
            raise ValueError("Records list should never be empty in SummaryGenerator")
        super().__init__(records, add_weights=True)
        self.week: WeekModel = self.records[0].week
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'week_summary'),
                                   output_directory=get_main_output_dir(self.records[0]),
                                   output_name=get_output_name('week_summary', self.week.week_no))
