from datetime import datetime


def is_date_in_range(_date, _start_date, _end_date):
    date = DateConverter.convert_to_date(_date)
    start_date = DateConverter.convert_to_date(_start_date)
    end_date = DateConverter.convert_to_date(_end_date)
    return start_date <= date <= end_date


class DateConverter:
    COMMON_VIEW_DATE_PATTERN = '%d.%m.%Y'

    @staticmethod
    def get_day(date):
        if isinstance(date, str):
            date = DateConverter.convert_to_date(date)
        return date.isoweekday()

    @staticmethod
    def convert_to_date(date: str, pattern=COMMON_VIEW_DATE_PATTERN):
        if isinstance(date, str):
            return datetime.strptime(date, pattern)
        return date

    @staticmethod
    def convert_date_to_string(date, pattern=COMMON_VIEW_DATE_PATTERN):
        if isinstance(date, datetime):
            return datetime.strftime(date, pattern)
        return date

    @staticmethod
    def replace_date_to_converted(data: dict, key):
        if data[key]:
            data[key] = DateConverter.convert_date_to_string(data[key])

    @staticmethod
    def get_year():
        now = datetime.now()
        return now.year
