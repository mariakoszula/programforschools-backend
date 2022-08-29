from configparser import ConfigParser, ExtendedInterpolation
from os import path, getcwd

config_parser = ConfigParser(interpolation=ExtendedInterpolation())
config_file = path.join(getcwd(), "config.ini")
config_parser.read_file(open(config_file, encoding='utf-8'))
