from configparser import ConfigParser, ExtendedInterpolation
from os import path, getcwd
from helpers.logger import app_logger
config_parser = ConfigParser(interpolation=ExtendedInterpolation())
app_logger.error(f"Get current dir: {getcwd()}")
config_file = path.join(getcwd(), "config.ini")
config_parser.read_file(open(config_file, encoding='utf-8'))
app_logger.debug(config_parser.get('DocTemplates', 'test').format(""))