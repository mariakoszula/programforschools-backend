from datetime import datetime
import re


def is_date_in_range(_date, _start_date, _end_date):
    date = DateConverter.convert_to_date(_date)
    start_date = DateConverter.convert_to_date(_start_date)
    end_date = DateConverter.convert_to_date(_end_date)
    return start_date <= date <= end_date


class DateConverter:
    COMMON_VIEW_DATE_PATTERN = '%d.%m.%Y'
    DATABASE_DATE_PATTERN = '%Y-%m-%d'
    pattern_matcher = {
        r'\d\d.\d\d.\d\d\d\d': COMMON_VIEW_DATE_PATTERN,
        r'\d\d\d\d-\d\d-\d\d': DATABASE_DATE_PATTERN
    }

    @staticmethod
    def get_day(date):
        if isinstance(date, str):
            date = DateConverter.convert_to_date(date)
        return date.isoweekday()

    @staticmethod
    def get_matching_pattern(date):
        for regex, pattern in DateConverter.pattern_matcher.items():
            if re.match(regex, date):
                return pattern
        raise ValueError("Date pattern not supported")

    @staticmethod
    def convert_to_date(date: str):
        if isinstance(date, str):
            pattern = DateConverter.get_matching_pattern(date)
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

    @staticmethod
    def two_digits(date_part):
        date_part_len = len(str(date_part))
        if date_part_len == 2:
            return "{}".format(date_part)
        elif date_part_len == 1:
            return "0{}".format(date_part)