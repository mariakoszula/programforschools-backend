from os import path
from typing import List

from documents_generator.DocumentGenerator import DocumentGenerator
from documents_generator.RecordGenerator import RecordGenerator
from helpers.common import get_output_name
from helpers.config_parser import config_parser
from helpers.date_converter import DateConverter
from models.product import ProductBoxModel, ProductStoreModel
from models.record import RecordModel
from models.week import WeekModel


class SummaryRecords:
    def __init__(self, records: List[RecordModel], boxes: List[ProductBoxModel] = None, add_weights=False):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        self.boxes = boxes
        self.records = records
        self.schools_delivery_rows = []
        self.product_summarize_rows = []
        self.add_weights = add_weights

    def prepare_data(self):
        self._schools_delivery_info()
        self._product_summarize_info()

    @staticmethod
    def __sum_products(records):
        return sum([r.delivered_kids_no for r in records])

    @staticmethod
    def __dict_from_list(data, get_key_fun):
        new_dict = {}
        for record in data:
            res = new_dict.get(get_key_fun(record), None)
            if res:
                res.append(record)
            else:
                new_dict[get_key_fun(record)] = [record]
        return new_dict

    def _prepare_school_delivery(self, nick, records):
        raise NotImplementedError("Needs to be implemented in derived class")

    def _schools_delivery_info(self):
        for nick, records in self.__dict_from_list(self.records, lambda record: record.contract.school.nick).items():
            self.schools_delivery_rows.append(self._prepare_school_delivery(nick, records))

    def _school_product_summarize(self, nick):
        if self.boxes is None or not len(self.boxes):
            return ""
        records = filter(lambda record: record.contract.school.nick == nick, self.records)
        results = []
        for product, records in self.__dict_from_list(records,
                                                      lambda record: record.product_store.product.name).items():
            sum_res = SummaryRecords.__sum_products(records)
            results.append(f"{product}: {self._get_amount_by_boxes(product, sum_res)}")
        return ", ".join(results)

    def _product_summarize_info(self):
        for product_store, records in self.__dict_from_list(self.records,
                                                            lambda record: record.product_store).items():
            self.product_summarize_rows.append(self._prepare_product_summarize(product_store, records))

    def _prepare_product_summarize(self, product_store: ProductStoreModel, records: List[RecordModel]):
        product_amount = SummaryRecords.__sum_products(records)
        if self.add_weights:
            weight = f"{product_amount * product_store.weight} {product_store.product.weight.name}"
            product_amount = f" {product_amount} [{weight}]"
        base = {
            "product": product_store.product.name,
            "products_sum": f"{product_amount}"}
        if self.boxes is not None:
            base["box_of_products"] = self._get_amount_by_boxes(product_store.product.name, product_amount)
        return base

    def _get_amount_by_boxes(self, product, amount):
        if self.boxes is None or not len(self.boxes):
            return ""
        try:
            product_box_info = next(filter(lambda b: b.product.name == product, self.boxes))
            (boxes, items) = divmod(amount, product_box_info.amount)
            return f"{boxes} opk., {items} szt."
        except StopIteration:
            return ""


def get_output_dir(record, delivery_date):
    return path.join(get_main_output_dir(record), delivery_date)


def get_main_output_dir(record):
    program_dir = record.contract.program.get_main_dir()
    return path.join(program_dir, config_parser.get('Directories', 'record'))


class DeliveryGenerator(SummaryRecords, DocumentGenerator):
    DAY_NAMES = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"]

    @staticmethod
    def _prepare_records_with_product(records: List[RecordModel]):
        return " + ".join([f"{str(record)}" for record in records])

    def _prepare_school_delivery(self, school_nick: str, records: List[RecordModel]):
        return {
            "school_nick": school_nick,
            "records_with_products": self._prepare_records_with_product(records),
            "box_with_products_for_school": self._school_product_summarize(school_nick)
        }

    @staticmethod
    def get_delivery_output_name(delivery_date, driver):
        return get_output_name('delivery', delivery_date, driver)

    def prepare_data(self):
        super().prepare_data()
        self.merge_rows("school_nick", self.schools_delivery_rows)
        self.merge_rows("product", self.product_summarize_rows)
        self.merge(
            driver=self.driver.upper(),
            delivery_date=self.delivery_date,
            delivery_day=DeliveryGenerator.DAY_NAMES[DateConverter.get_day(self.delivery_date)].upper(),
            comments=self.comments,
            boxes='' if not len(self.boxes) else f'Opakowania: {",".join([str(box) for box in self.boxes])}'
        )

    def __init__(self, records: List[RecordModel], date, driver, boxes: List[ProductBoxModel], comments=None):
        super().__init__(records, boxes)
        self.delivery_date = date
        self.driver = driver
        self.comments = comments
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'delivery'),
                                   output_directory=get_output_dir(self.records[0], self.delivery_date),
                                   output_name=self.get_delivery_output_name(self.delivery_date, self.driver))


class DeliveryRecordsGenerator(DocumentGenerator):
    def prepare_data(self):
        self.merge_pages([RecordGenerator.prepare_data_to_fill(record) for record in self.records])

    def __init__(self, records, date, driver, **_):
        self.records = records
        output_directory = get_output_dir(self.records[0], date)
        DocumentGenerator.__init__(self,
                                   template_document=RecordGenerator.get_template(),
                                   output_directory=output_directory,
                                   output_name=get_output_name('record_all', date, driver))


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

    def _prepare_school_delivery(self, nick, records: List[RecordModel]):
        fruit_d = prepare_product_dict(FRUIT, [r for r in records if r.product_store.product.type.is_fruit_veg()])
        dairy_d = prepare_product_dict(DAIRY, [r for r in records if r.product_store.product.type.is_dairy()])
        return  dict({"school_nick": nick}.items() | fruit_d.items() | dairy_d.items())

    def prepare_data(self):
        super().prepare_data()
        self.merge_rows("school_nick", self.schools_delivery_rows)
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
