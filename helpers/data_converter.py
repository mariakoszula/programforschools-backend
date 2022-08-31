from datetime import datetime


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
