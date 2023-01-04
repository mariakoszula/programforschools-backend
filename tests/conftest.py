import pytest
import sqlalchemy.exc

from helpers.db import db

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
    GoogleDriveCommands.clean_main_directory()


class InitialSetupError(BaseException):
    pass


@pytest.fixture(scope="module")
def initial_program_setup(_db):
    company = CompanyModel(**common_data.company)
    company.save_to_db()
    program = ProgramModel(**common_data.get_program_data(company.id))
    program.save_to_db()
    main_directory = None
    try:
        main_directory = DirectoryCreator.create_main_directory_tree(program)
        main_directory.save_to_db()
    except sqlalchemy.exc.NoResultFound as e:
        print(e)
        raise InitialSetupError(main_directory)
    yield program
    GoogleDriveCommands.clean_main_directory()
