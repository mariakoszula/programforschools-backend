from os import path
from typing import List

from documents_generator.DocumentGenerator import DocumentGenerator
from documents_generator.RecordGenerator import RecordGenerator
from helpers.common import get_output_name
from helpers.config_parser import config_parser
from helpers.date_converter import DateConverter
from helpers.file_folder_creator import DirectoryCreator
from models.product import ProductBoxModel
from models.record import RecordModel


class DeliveryGenerator(DocumentGenerator):
    DAY_NAMES = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"]

    @staticmethod
    def get_delivery_output_name(delivery_date, driver):
        return get_output_name('delivery', delivery_date, driver)

    def prepare_data(self):
        self.__schools_delivery_info()
        self.merge_rows("school_nick", self.schools_delivery_rows)
        self.__product_summarize_info()
        self.merge_rows("product", self.product_summarize_rows)
        self.merge(
            driver=self.driver.upper(),
            delivery_date=self.delivery_date,
            delivery_day=DeliveryGenerator.DAY_NAMES[DateConverter.get_day(self.delivery_date)].upper(),
            comments=self.comments,
            boxes='' if not len(self.boxes) else f'Opakowania: {",".join([str(box) for box in self.boxes])}'
        )

    def __init__(self, records: List[RecordModel], date, driver, boxes: List[ProductBoxModel], comments=None):
        if not len(records):
            raise ValueError("List with records cannot be empty")
        self.records = records
        self.delivery_date = date
        self.driver = driver
        self.comments = comments
        self.boxes = boxes
        self.schools_delivery_rows = []
        self.product_summarize_rows = []
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'delivery'),
                                   output_directory=self.get_output_dir(self.records[0], self.delivery_date),
                                   output_name=self.get_delivery_output_name(self.delivery_date, self.driver))

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

    def __schools_delivery_info(self):
        for nick, records in self.__dict_from_list(self.records, lambda record: record.contract.school.nick).items():
            self.schools_delivery_rows.append(self.__prepare_school_delivery(nick, records))

    def __prepare_school_delivery(self, school_nick: str, records: List[RecordModel]):
        return {
            "school_nick": school_nick,
            "records_with_products": DeliveryGenerator.__prepare_records_with_product(records),
            "box_with_products_for_school": self.__school_product_summarize(school_nick)
        }

    def __school_product_summarize(self, nick):
        if not len(self.boxes):
            return ""
        records = filter(lambda record: record.contract.school.nick == nick, self.records)
        results = []
        for product, records in self.__dict_from_list(records,
                                                      lambda record: record.product_store_diary.product.name).items():
            sum_res = DeliveryGenerator.__sum_products(records)
            results.append(f"{product}: {self.__get_amount_by_boxes(product, sum_res)}")
        return ", ".join(results)

    def __product_summarize_info(self):
        for product, records in self.__dict_from_list(self.records,
                                                      lambda record: record.product_store_diary.product.name).items():
            self.product_summarize_rows.append(self.__prepare_product_summarize(product, records))

    def __prepare_product_summarize(self, product, records: List[RecordModel]):
        product_amount = DeliveryGenerator.__sum_products(records)
        return {
            "product": product,
            "products_sum": str(product_amount),
            "box_of_products": self.__get_amount_by_boxes(product, product_amount)
        }

    def __get_amount_by_boxes(self, product, amount):
        if not len(self.boxes):
            return ""
        try:
            product_box_info = next(filter(lambda b: b.product.name == product, self.boxes))
            (boxes, items) = divmod(amount, product_box_info.amount)
            return f"{boxes} opk., {items} szt."
        except StopIteration:
            return ""

    @staticmethod
    def get_output_dir(record, delivery_date):
        program_dir = DirectoryCreator.get_main_dir(school_year=record.contract.program.school_year,
                                                    semester_no=record.contract.program.semester_no)
        return path.join(program_dir, config_parser.get('Directories', 'record'), delivery_date)

    @staticmethod
    def __sum_products(records):
        return sum([r.delivered_kids_no for r in records])

    @staticmethod
    def __prepare_records_with_product(records: List[RecordModel]):
        return " + ".join([str(record) for record in records])


class DeliveryRecordsGenerator(DocumentGenerator):
    def prepare_data(self):
        self.merge_pages([RecordGenerator.prepare_data_to_fill(record) for record in self.records])

    def __init__(self, records, date, driver, **_):
        self.records = records
        output_directory = DeliveryGenerator.get_output_dir(self.records[0], date)
        DocumentGenerator.__init__(self,
                                   template_document=RecordGenerator.get_template(),
                                   output_directory=output_directory,
                                   output_name=get_output_name('record_all', date, driver))
