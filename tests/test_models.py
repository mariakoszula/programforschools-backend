import pytest

from models.application import ApplicationModel, ApplicationType
from models.invoice import SupplierModel, InvoiceModel, InvoiceProductModel
from models.contract import ContractModel, AnnexModel
from models.week import WeekModel
from models.product import ProductTypeModel, ProductStoreModel
from models.record import RecordModel, RecordState
from tests.common import add_record
from tests.common_data import school_data, annex_data, week_data
from helpers.date_converter import DateConverter


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
    timed_end_date = AnnexModel.find_by_id(annex.id).timed_annex[0].validity_date_end
    assert DateConverter.convert_date_to_string(timed_end_date, pattern="%Y-%m-%d") == proper_end_date


def test_week(week):
    week = WeekModel.find(week.week_no, week.program_id)
    assert week.week_no == 1
    week_by_date = WeekModel.find_by_date("2023-12-15")
    assert week_by_date.week_no == 1
    with pytest.raises(ValueError):
        WeekModel(week_no=2, start_date="2023-01-11", end_date="2022-12-12", program_id=week.program_id)


def test_product(product_store_milk):
    store = ProductStoreModel.find(product_store_milk.program_id, ProductTypeModel.DAIRY_TYPE)[0]
    assert store is not None and store.product.name == "milk"
    store_find_by_name = ProductStoreModel.find_by(product_store_milk.program_id, "milk")
    assert store_find_by_name is not None and store_find_by_name.min_amount == 5


@pytest.fixture(scope="class")
def setup_record_test_init(contract_for_school, product_store_milk, week):
    contract_for_school.update_db(dairy_products=5, fruitVeg_products=10)  # 2023-01-01
    AnnexModel(contract_for_school, **annex_data)  # 2023-12-07
    AnnexModel(contract_for_school, validity_date="2023-12-08", dairy_products=11, fruitVeg_products=12,
               validity_date_end="2023-12-12")
    AnnexModel(contract_for_school, validity_date="2023-12-09", dairy_products=22, fruitVeg_products=23,
               validity_date_end="2023-12-13")
    yield contract_for_school, product_store_milk, week
    RecordModel.query.delete()


@pytest.mark.parametrize("date,expected_kids_no,expected_min_amount", [("01.12.2023", 5, False),
                                                                       ("07.12.2023", 1, False),
                                                                       ("08.12.2023", 11, False),
                                                                       ("12.12.2023", 22, False),
                                                                       ("15.12.2023", 1, True)])
def test_record_model(date, expected_kids_no, expected_min_amount, setup_record_test_init):
    contract, product_store_dairy, _ = setup_record_test_init
    r = RecordModel(date, contract.id, product_store_dairy)
    r.save_to_db()
    r.change_state(RecordState.PLANNED)
    r.change_state(RecordState.GENERATION_IN_PROGRESS, date=date)
    r.change_state(RecordState.GENERATED)
    assert r.delivered_kids_no == expected_kids_no
    assert product_store_dairy.is_min_amount_exceeded(school_data["nick"]) is False


def test_week_overlap_throws_value_error(week):
    week_two = WeekModel(week_no=2, start_date=week_data["start_date"], end_date=week_data["end_date"],
                         program_id=week.program_id)
    with pytest.raises(ValueError):
        WeekModel.find_by_date(week_data["start_date"])
    week_two.delete_from_db()


def test_invoice_model(product_store_milk, product_store_kohlrabi):
    supplier = SupplierModel("Long name for supplier", "supplier nickname")
    assert str(supplier) == "Long name for supplier <supplier nickname>"
    assert supplier.id is not None
    invoice = InvoiceModel("RL 123z", "30.12.2022", supplier.id, product_store_milk.program_id)
    assert str(invoice) == "Invoice 'RL 123z' from 'supplier nickname' on 30.12.2022"
    assert invoice.id is not None
    second_invoice = InvoiceModel("TH new", "2023-01-08", supplier.id, product_store_milk.program_id)
    assert str(second_invoice) == "Invoice 'TH new' from 'supplier nickname' on 08.01.2023"

    product = InvoiceProductModel(invoice.id, product_store_milk.id, 500)
    assert str(product) == "Numer faktury RL 123z: milk 500.0L"
    assert product.id is not None
    product_second = InvoiceProductModel(invoice.id, product_store_kohlrabi.id, 20.5)
    assert str(product_second) == "Numer faktury RL 123z: kohlrabi 20.5KG"
    assert product_second.id is not None


def test_application_setup(setup_record_test_init, second_week):
    contract, _, week = setup_record_test_init
    weeks = [week, second_week]
    assert ApplicationModel.possible_types(week.program_id) == [ApplicationType.FULL, ApplicationType.DAIRY,
                                                                ApplicationType.FRUIT_VEG]
    application = ApplicationModel(week.program_id, [contract], weeks, ApplicationType.FULL)
    assert ApplicationModel.possible_types(week.program_id) == [ApplicationType.FULL]
    assert str(application) == "2/1/2022/2023"
    with pytest.raises(ValueError):
        ApplicationModel(week.program_id, [contract], weeks, ApplicationType.DAIRY)
    application_other = ApplicationModel(week.program_id, [contract], weeks, ApplicationType.FULL)
    assert str(application_other) == "2/2/2022/2023"
    application_other.delete_from_db()
    application.delete_from_db()


def test_filter_records(setup_record_test_init, second_week, third_week,
                        product_store_apple, product_store_carrot,
                        second_contract_for_school, contract_for_school_no_dairy):
    first_contract, product_store_dairy, week = setup_record_test_init
    application_dairy = ApplicationModel(week.program_id,
                                         [first_contract, second_contract_for_school, contract_for_school_no_dairy],
                                         [week, second_week], ApplicationType.DAIRY)
    application_fruit_veg = ApplicationModel(week.program_id,
                                             [first_contract, contract_for_school_no_dairy],
                                             [week, second_week], ApplicationType.FRUIT_VEG)
    second_application_dairy = ApplicationModel(week.program_id,
                                                [second_contract_for_school, contract_for_school_no_dairy],
                                                [third_week], ApplicationType.DAIRY)
    first_contract_dairy_week_1 = add_record("01.12.2023", first_contract.id, product_store_dairy)
    first_contract_fruit_week_2 = add_record("17.12.2023", first_contract.id, product_store_apple)
    contract_for_school_no_dairy_week_2 = add_record("17.12.2023", contract_for_school_no_dairy.id, product_store_apple)
    contract_for_school_no_dairy_veg_week_2 = add_record("18.12.2023", contract_for_school_no_dairy.id,
                                                         product_store_carrot)
    add_record("01.12.2023", second_contract_for_school.id, product_store_apple)

    first_contract_dairy_week_1_generated = add_record("02.12.2023", first_contract.id, product_store_dairy,
                                                       RecordState.GENERATED)
    second_contract_dairy_week_1 = add_record("03.12.2023", second_contract_for_school.id, product_store_dairy)
    second_contract_dairy_week_3 = add_record("29.12.2023", second_contract_for_school.id, product_store_dairy)

    application_dairy_records = RecordModel.filter_records(application_dairy)
    assert len(application_dairy_records) == 2
    assert application_dairy_records[0].id == first_contract_dairy_week_1.id
    assert application_dairy_records[1].id == second_contract_dairy_week_1.id
    assert RecordModel.filter_records_by_contract(application_dairy, first_contract)[0].id \
           == first_contract_dairy_week_1.id
    application_dairy_records_generated = RecordModel.filter_records(application_dairy, state=RecordState.GENERATED)
    assert len(application_dairy_records_generated) == 1
    assert application_dairy_records_generated[0].id == first_contract_dairy_week_1_generated.id

    application_fruit_veg_records = RecordModel.filter_records(application_fruit_veg)
    assert len(application_fruit_veg_records) == 3
    assert application_fruit_veg_records[0].id == first_contract_fruit_week_2.id
    assert application_fruit_veg_records[1].id == contract_for_school_no_dairy_week_2.id
    assert application_fruit_veg_records[2].id == contract_for_school_no_dairy_veg_week_2.id

    assert len(RecordModel.filter_records_by_contract(application_fruit_veg, contract_for_school_no_dairy)) == 2

    second_application_dairy_record = RecordModel.filter_records(second_application_dairy)
    assert len(second_application_dairy_record) == 1
    assert second_application_dairy_record[0].id == second_contract_dairy_week_3.id
    application_dairy.delete_from_db()
    application_fruit_veg.delete_from_db()
    second_application_dairy.delete_from_db()
