import pytest
import sqlalchemy.exc

from helpers.db import db
from app import create_app
import psycopg2
from helpers.config_parser import config_parser
from models.application import ApplicationModel, ApplicationType
from models.company import CompanyModel
from models.contract import ContractModel, AnnexModel
from models.invoice import SupplierModel, InvoiceModel, InvoiceProductModel, InvoiceDisposalModel
from models.product import ProductTypeModel, WeightTypeModel, ProductStoreModel, ProductModel
from models.program import ProgramModel
import tests.common_data as common_data
from helpers.google_drive import GoogleDriveCommands
from helpers.file_folder_creator import DirectoryCreator
from models.record import RecordModel
from models.school import SchoolModel
from models.week import WeekModel
from tests.common import clear_tables_schools, clear_tables_common
from flask_jwt_extended import create_access_token
from models.user import UserModel, Role, AllowedRoles

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
    clear_tables_schools()


@pytest.fixture(scope="module")
def second_contract_for_school(program_setup):
    school = SchoolModel(nick="SecondSchool",
                         city="CitySecond",
                         name="SecondSchoolName",
                         nip="098746623",
                         regon="74983579023",
                         address="street 2")
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    contract.update_db(dairy_products=1, fruitVeg_products=22)
    yield contract
    clear_tables_schools()


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
    clear_tables_schools()


@pytest.fixture(scope="module")
def contract_for_school_no_fruit(program_setup):
    school = SchoolModel(nick="NoFruitInSchool",
                         city="NoFruitCity",
                         name="NoFruitInSchoolName",
                         nip="xxxxxxxxx",
                         regon="yyyyyyyyy",
                         address="ssssssssss")
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    contract.update_db(dairy_products=43, fruitVeg_products=0)
    yield contract
    clear_tables_schools()



@pytest.fixture(scope="module")
def week(program_setup):
    yield WeekModel(**common_data.week_data, program_id=program_setup.id)
    clear_tables_schools()


@pytest.fixture(scope="module")
def second_week(program_setup):
    yield WeekModel(week_no=2, start_date="2023-12-17", end_date="2023-12-22", program_id=program_setup.id)
    clear_tables_common()


@pytest.fixture(scope="module")
def third_week(program_setup):
    yield WeekModel(week_no=3, start_date="2023-12-23", end_date="2023-12-30", program_id=program_setup.id)
    clear_tables_common()


@pytest.fixture(scope="module")
def weight_type_kg():
    yield WeightTypeModel("KG")


@pytest.fixture(scope="module")
def weight_type_liter():
    yield WeightTypeModel("L")


@pytest.fixture(scope="module")
def fruit():
    yield ProductTypeModel(ProductTypeModel.FRUIT_TYPE)


@pytest.fixture(scope="module")
def vegetable():
    yield ProductTypeModel(ProductTypeModel.VEGETABLE_TYPE)


@pytest.fixture(scope="module")
def dairy():
    yield ProductTypeModel(ProductTypeModel.DAIRY_TYPE)


@pytest.fixture(scope="module")
def product_store_apple(program_setup, weight_type_kg, fruit):
    product = ProductModel("apple", ProductTypeModel.FRUIT_TYPE, "KG", vat=5)
    product.update_db(template_name="apple")
    yield ProductStoreModel(program_setup.id, "apple", 1, 0.25)


@pytest.fixture(scope="module")
def product_store_juice(program_setup, weight_type_liter, fruit):
    product = ProductModel("juice", ProductTypeModel.FRUIT_TYPE, "L", vat=22)
    product.update_db(template_name="juice")
    yield ProductStoreModel(program_setup.id, "juice", 1, 0.25)


@pytest.fixture(scope="module")
def product_store_carrot(program_setup, weight_type_kg, vegetable):
    product = ProductModel("carrot", ProductTypeModel.VEGETABLE_TYPE, "KG", vat=8)
    product.update_db(template_name="carrot")
    yield ProductStoreModel(program_setup.id, "carrot", 4, 0.10)


@pytest.fixture(scope="module")
def product_store_kohlrabi(program_setup, weight_type_kg, vegetable):
    product = ProductModel("kohlrabi", ProductTypeModel.VEGETABLE_TYPE, "KG")
    product.update_db(template_name="kohlrabi")
    yield ProductStoreModel(program_setup.id, "kohlrabi", 4, 0.09)


@pytest.fixture(scope="module")
def product_store_milk(program_setup, weight_type_liter, dairy):
    product = ProductModel("milk", ProductTypeModel.DAIRY_TYPE, "L", vat=7)
    product.update_db(template_name="milk")
    yield ProductStoreModel(program_setup.id, "milk", 5, 0.25)


@pytest.fixture(scope="module")
def product_store_yoghurt(program_setup, weight_type_kg, dairy):
    product = ProductModel("yoghurt", ProductTypeModel.DAIRY_TYPE, "KG", vat=2)
    product.update_db(template_name="yoghurt")
    yield ProductStoreModel(program_setup.id, "yoghurt", 2, 0.15)


@pytest.fixture(scope="module")
def setup_record_test_init(contract_for_school, product_store_milk, week):
    contract_for_school.update_db(dairy_products=5, fruitVeg_products=10)  # 2023-01-01
    AnnexModel(contract_for_school, **common_data.annex_data)  # 2023-12-07
    AnnexModel(contract_for_school, validity_date="2023-12-08", dairy_products=11, fruitVeg_products=12,
               validity_date_end="2023-12-12")
    AnnexModel(contract_for_school, validity_date="2023-12-09", dairy_products=22, fruitVeg_products=23,
               validity_date_end="2023-12-13")
    yield contract_for_school, product_store_milk, week
    RecordModel.query.delete()


@pytest.fixture(scope="module")
def create_application(setup_record_test_init, second_week):
    contract, _, week = setup_record_test_init
    weeks = [week, second_week]
    application = ApplicationModel(week.program_id, [contract], weeks, ApplicationType.FULL)
    yield application, weeks, contract


@pytest.fixture(scope="function")
def invoice_data(product_store_milk, product_store_kohlrabi, product_store_apple, create_application):
    supplier = SupplierModel("Long name for supplier", "supplier nickname")
    invoices = []
    products = []
    invoice_disposals = []
    invoices.append(InvoiceModel("RL 123z", "30.12.2022", supplier.id, product_store_milk.program_id))
    invoices.append(InvoiceModel("TH new", "2023-01-08", supplier.id, product_store_milk.program_id))
    invoices.append(InvoiceModel("Another", "2023-02-09", supplier.id, product_store_milk.program_id))
    products.append(InvoiceProductModel(invoices[0].id, product_store_milk.id, 500))
    products.append(InvoiceProductModel(invoices[0].id, product_store_kohlrabi.id, 20.5))
    products.append(InvoiceProductModel(invoices[1].id, product_store_apple.id, 12.3))
    products.append(InvoiceProductModel(invoices[2].id, product_store_milk.id, 10))
    products.append(InvoiceProductModel(invoices[2].id, product_store_apple.id, 10))
    application, _, _ = create_application

    invoice_disposals.append(InvoiceDisposalModel(products[0].id, application.id, 500))
    invoice_disposals.append(InvoiceDisposalModel(products[1].id, application.id, 15))
    invoice_disposals.append(InvoiceDisposalModel(products[2].id, application.id, 12.3))
    invoice_disposals.append(InvoiceDisposalModel(products[3].id, application.id, 8))
    invoice_disposals.append(InvoiceDisposalModel(products[4].id, application.id, 5))
    yield invoices, products, supplier, invoice_disposals
    for invoice_disposal in invoice_disposals:
        invoice_disposal.delete_from_db()
    for product in products:
        product.delete_from_db()
    supplier.delete_from_db()


@pytest.fixture(scope="session")
def auth_headers():
    role = Role(AllowedRoles.admin)
    role.save_to_db()
    user = UserModel("test_user", "test_user", "test_user@com.pl", AllowedRoles.admin)
    user.save_to_db()
    token = create_access_token(identity=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client_with_in_memory_db():
    """Setup a Flask test client and an in-memory database."""
    app_ = create_app()
    app_.config["TESTING"] = True
    app_.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory database
    app_.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app_.app_context():
        GoogleDriveCommands.clean_main_directory()
        db.drop_all()
        db.create_all()
        yield app_.test_client()
        db.drop_all()
