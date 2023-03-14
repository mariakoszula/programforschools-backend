import pytest

from models.invoice import SupplierModel, InvoiceModel, InvoiceProductModel
from models.school import SchoolModel
from models.contracts import ContractModel, AnnexModel
from models.week import WeekModel
from models.product import ProductModel, WeightTypeModel, ProductTypeModel, ProductStoreModel
from models.record import RecordModel, RecordState
from tests.common_data import school_data, annex_data, week_data
from helpers.date_converter import DateConverter


@pytest.fixture(scope="module")
def contract_for_school(program_setup):
    school = SchoolModel(**school_data)
    school.save_to_db()
    contract = ContractModel(school.id, program_setup)
    contract.save_to_db()
    yield contract


def test_school_model_with_contract(contract_for_school):
    contract = ContractModel.find(contract_for_school.program_id, contract_for_school.school_id)
    assert contract is not None and contract.school.nick == school_data["nick"] \
           and contract.contract_no == "1"


def test_timed_annex(contract_for_school):
    contract = ContractModel.find(contract_for_school.program_id, contract_for_school.school_id)
    with pytest.raises(ValueError):
        date_lower_than_validity_start = "2022-12-06"
        AnnexModel(contract, **annex_data, validity_date_end=date_lower_than_validity_start)
    proper_end_date = "2023-12-09"
    annex = AnnexModel(contract, **annex_data, validity_date_end=proper_end_date)
    assert annex.no == 1
    assert annex.id == 1
    timed_end_date = AnnexModel.find_by_id(annex.id).timed_annex[0].validity_date_end
    assert DateConverter.convert_date_to_string(timed_end_date, pattern="%Y-%m-%d") == proper_end_date


@pytest.fixture(scope="module")
def week(program_setup):
    yield WeekModel(**week_data, program_id=program_setup.id)


def test_week(week):
    week = WeekModel.find(week.week_no, week.program_id)
    assert week.week_no == 1
    week_by_date = WeekModel.find_by_date("2023-12-15")
    assert week_by_date.week_no == 1
    with pytest.raises(ValueError):
        WeekModel(week_no=2, start_date="2023-01-11", end_date="2022-12-12", program_id=week.program_id)


@pytest.fixture(scope="module")
def product_store(program_setup):
    WeightTypeModel("L")
    ProductTypeModel(ProductTypeModel.DAIRY_TYPE)
    ProductModel("milk", ProductTypeModel.DAIRY_TYPE, "L")
    yield ProductStoreModel(program_setup.id, "milk", 5, 0.25)


def test_product(product_store):
    store = ProductStoreModel.find(product_store.program_id, ProductTypeModel.DAIRY_TYPE).one()
    assert store is not None and store.product.name == "milk"
    store_find_by_name = ProductStoreModel.find_by(product_store.program_id, "milk")
    assert store_find_by_name is not None and store_find_by_name.min_amount == 5


@pytest.fixture(scope="module")
def setup_record_test_init(contract_for_school, product_store, week):
    contract_for_school.update_db(dairy_products=5)  # 2023-01-01
    AnnexModel(contract_for_school, **annex_data)  # 2023-12-07
    AnnexModel(contract_for_school, validity_date="2023-12-08", dairy_products=11,
               validity_date_end="2023-12-12")
    AnnexModel(contract_for_school, validity_date="2023-12-09", dairy_products=22,
               validity_date_end="2023-12-13")
    yield contract_for_school.id, product_store
    RecordModel.query.delete()
    WeekModel.query.delete()


@pytest.mark.parametrize("date,expected_kids_no,expected_min_amount", [("01.12.2023", 5, False),
                                                                       ("07.12.2023", 1, False),
                                                                       ("08.12.2023", 11, False),
                                                                       ("12.12.2023", 22, False),
                                                                       ("15.12.2023", 1, True)])
def test_record_model(date, expected_kids_no, expected_min_amount, setup_record_test_init):
    contract_id, product_store = setup_record_test_init
    r = RecordModel(date, contract_id, product_store)
    r.save_to_db()
    r.change_state(RecordState.PLANNED)
    r.change_state(RecordState.GENERATION_IN_PROGRESS, date=date)
    r.change_state(RecordState.GENERATED)
    assert r.delivered_kids_no == expected_kids_no
    assert product_store.is_min_amount_exceeded(school_data["nick"]) is expected_min_amount


def test_week_overlap_throws_value_error(week):
    WeekModel(week_no=2, start_date=week_data["start_date"], end_date=week_data["end_date"],
              program_id=week.program_id)
    with pytest.raises(ValueError):
        WeekModel.find_by_date(week_data["start_date"])


def test_invoice_model(product_store):
    supplier = SupplierModel("Long name for supplier", "supplier nickname")
    assert str(supplier) == "Long name for supplier <supplier nickname>"
    assert supplier.id is not None
    invoice = InvoiceModel("RL 123z", "30.12.2022", supplier.id, product_store.program_id)
    assert str(invoice) == "Invoice 'RL 123z' from 'supplier nickname' on 30.12.2022"
    assert invoice.id is not None
    second_invoice = InvoiceModel("TH new", "2023-01-08", supplier.id, product_store.program_id)
    assert str(second_invoice) == "Invoice 'TH new' from 'supplier nickname' on 08.01.2023"

    product = InvoiceProductModel(invoice.id, product_store.id, 500)
    assert str(product) == "InvoiceNo RL 123z: milk 500.0L"
    assert product.id is not None
