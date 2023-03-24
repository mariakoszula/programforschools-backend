import pytest
import sqlalchemy.exc

from helpers.db import db
from app import create_app
import psycopg2
from helpers.config_parser import config_parser
from models.company import CompanyModel
from models.contract import ContractModel, AnnexModel
from models.product import ProductTypeModel, WeightTypeModel, ProductStoreModel, ProductModel
from models.program import ProgramModel
import tests.common_data as common_data
from helpers.google_drive import GoogleDriveCommands
from helpers.file_folder_creator import DirectoryCreator
from models.record import RecordModel
from models.school import SchoolModel
from models.week import WeekModel
from tests.common import clear_tables

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


@pytest.fixture(scope="module")
def contract_for_school(program_setup):
    school = SchoolModel(**common_data.school_data)
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    yield contract
    clear_tables()


@pytest.fixture(scope="module")
def second_contract_for_school(program_setup):
    school = SchoolModel(nick="SecondSchool")
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    contract.update_db(dairy_products=1, fruitVeg_products=2)
    yield contract
    clear_tables()


@pytest.fixture(scope="module")
def contract_for_school_no_dairy(program_setup):
    school = SchoolModel(nick="NoDairyContractSchool",
                         city="City",
                         name="NoDairyContractSchool",
                         nip="1234567890",
                         regon="123456789",
                         address="street 123")
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    contract.update_db(dairy_products=0, fruitVeg_products=3)
    yield contract
    clear_tables()


@pytest.fixture(scope="module")
def week(program_setup):
    yield WeekModel(**common_data.week_data, program_id=program_setup.id)
    clear_tables()


@pytest.fixture(scope="module")
def second_week(program_setup):
    yield WeekModel(week_no=2, start_date="2023-12-17", end_date="2023-12-22", program_id=program_setup.id)
    clear_tables()


@pytest.fixture(scope="module")
def third_week(program_setup):
    yield WeekModel(week_no=3, start_date="2023-12-23", end_date="2023-12-30", program_id=program_setup.id)
    clear_tables()


@pytest.fixture(scope="module")
def weight_type_kg():
    yield WeightTypeModel("KG")


@pytest.fixture(scope="module")
def product_store_fruit(program_setup, weight_type_kg):
    ProductTypeModel(ProductTypeModel.FRUIT_TYPE)
    product = ProductModel("apple", ProductTypeModel.FRUIT_TYPE, "KG")
    product.update_db(template_name="apple")
    yield ProductStoreModel(program_setup.id, "apple", 1, 0.25)


@pytest.fixture(scope="module")
def product_store_vegetable(program_setup, weight_type_kg):
    ProductTypeModel(ProductTypeModel.VEGETABLE_TYPE)
    product = ProductModel("carrot", ProductTypeModel.VEGETABLE_TYPE, "KG")
    product.update_db(template_name="carrot")
    yield ProductStoreModel(program_setup.id, "carrot", 4, 0.10, vat=8)
