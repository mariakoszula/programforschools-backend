import pytest
import sqlalchemy.exc

from helpers.db import db
from os import environ
from app import create_app
import psycopg2
from helpers.config_parser import config_parser
from models.company import CompanyModel
from models.program import ProgramModel
import tests.common_data as common_data
from helpers.google_drive import GoogleDriveCommands
from helpers.file_folder_creator import DirectoryCreator

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope='session')
def database(request):
    conn = psycopg2.connect(dbname=config_parser.get("Database", "user"),
                            user=config_parser.get("Database", "user"),
                            password=config_parser.get("Database", "password"),
                            host=config_parser.get("Database", "host"),
                            port=config_parser.get("Database", "port"))

    @request.addfinalizer
    def drop_all_tables():
        cursor = conn.cursor()
        sql = '''DROP SCHEMA public CASCADE;CREATE SCHEMA public;'''
        cursor.execute(sql)
        conn.commit()
        conn.close()


@pytest.fixture(scope='session')
def _db(app):
    from flask_sqlalchemy import SQLAlchemy
    _db = SQLAlchemy(app=app)
    return _db


@pytest.fixture(scope='session')
def app(database):
    app = create_app()
    with app.app_context():
        GoogleDriveCommands.clean_main_directory()
        db.drop_all()
        db.create_all()
        yield app


class InitialSetupError(BaseException):
    pass


class Filter:
    def __init__(self, **kwargs):
        self.filter = kwargs


def create_if_not_exists(model, custom_filter: Filter, **kwargs):
    found = model.find_by(**custom_filter.filter)
    if not found:
        res = model(**kwargs)
        res.save_to_db()
        return res
    return found


@pytest.fixture(scope="module")
def program_setup(_db):
    company = create_if_not_exists(CompanyModel, Filter(name=common_data.company["name"]), **common_data.company)
    program = create_if_not_exists(ProgramModel, Filter(semester_no=common_data.program["semester_no"],
                                                        school_year=common_data.program["school_year"]),
                                   **common_data.get_program_data(company.id))
    yield program


@pytest.fixture(scope="module")
def initial_app_setup(program_setup):
    program = program_setup
    main_directory = None
    try:
        main_directory = DirectoryCreator.create_main_directory_tree(program)
        main_directory.save_to_db()
    except sqlalchemy.exc.NoResultFound as e:
        print(e)
        raise InitialSetupError(main_directory)
    yield program
    GoogleDriveCommands.clean_main_directory()
