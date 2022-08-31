from json import JSONEncoder
from datetime import datetime


class ObjectJsonEncoder(JSONEncoder):
    def default(self, obj):
        return obj.__dict__


def to_json(list_of_objects):
    return [ObjectJsonEncoder().encode(item) for item in list_of_objects]


class DataConverter:
    COMMON_VIEW_DATE_PATTERN = '%d.%m.%Y'

    @staticmethod
    def convert_to_date(date: str, pattern=COMMON_VIEW_DATE_PATTERN):
        if isinstance(date, str):
            return datetime.strptime(date, pattern)

    @staticmethod
    def convert_date_to_string(date, pattern=COMMON_VIEW_DATE_PATTERN):
        return datetime.strftime(date, pattern)

    @staticmethod
    def replace_date_to_converted(data: dict, key):
        if data[key]:
            data[key] = DataConverter.convert_date_to_string(data[key])
