import pytest

from documents_generator.ApplicationGenerator import get_application_dir, get_application_dir_per_school, \
    RecordsSummaryGenerator, StatementGenerator, application_factory, ApplicationGenerator
from models.application import ApplicationModel, ApplicationType
from os import path

from models.contract import AnnexModel
from models.record import RecordModel
from tests import common_data
from tests.common import all_fields_to_marge_are_in_file, add_record, GoogleDriveFakeCommands


def validate_document_creation(obj, gen, name_output):
    assert obj.remote_parent.name == f"gen/{name_output}"
    obj.generate()
    assert isinstance(obj, gen)
    assert len(obj.generated_documents) == 1
    assert path.isdir(obj.output_directory)
    assert obj.generated_documents[0].name == f"gen/{name_output}"


def assert_value(value, expected, precision=0):
    assert f"{value}" == f"{expected:.{precision}f}"


def test_application_generator_fruit_veg(contract_for_school_no_dairy, week, second_week, third_week,
                                         product_store_fruit, product_store_vegetable):
    assert week.program_id == second_week.program_id == third_week.program_id
    application = ApplicationModel(week.program_id, [contract_for_school_no_dairy], [week, second_week, third_week],
                                   ApplicationType.FRUIT_VEG)

    #TODO add second contract
    assert get_application_dir(application) == "TEST_PROGRAM_2022_2023_SEMESTR_2/WNIOSKI/2_1_2022_2023_warzywa-owoce"
    assert get_application_dir_per_school(
        application) == "TEST_PROGRAM_2022_2023_SEMESTR_2/WNIOSKI/2_1_2022_2023_warzywa-owoce/EWIDENCJE"
    records = RecordModel.filter_records_by_contract(application, contract_for_school_no_dairy)
    with pytest.raises(ValueError):
        RecordsSummaryGenerator(application, records, "30.12.2023")
    AnnexModel(contract_for_school_no_dairy, validity_date="21.12.2023", fruitVeg_products=100)
    add_record("15.12.2023", contract_for_school_no_dairy.id, product_store_fruit)  # 3 kids no
    add_record("30.12.2023", contract_for_school_no_dairy.id, product_store_vegetable)  # 100 kids no
    add_record("18.12.2023", contract_for_school_no_dairy.id, product_store_fruit)  # 3 kids no
    add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_vegetable)  # 100 kids no

    app_date = "30.12.2023"
    application_generator = application_factory(application, app_date, start_week=1, is_last=False,
                                                _output_dir="gen", _drive_tool=GoogleDriveFakeCommands)
    record_summary = application_generator.records_summary[0]
    validate_document_creation(record_summary, RecordsSummaryGenerator, "NoDairyContractSchool_Ewidencja_dostaw.docx")
    all_fields_to_marge_are_in_file(record_summary.generated_documents[0].name,
                                    school_name="NoDairyContractSchool",
                                    school_regon="123456789",
                                    school_nip="1234567890",
                                    school_address="street 123",
                                    date_day="30",
                                    date_month="12",
                                    date_year="2023",
                                    city="City",
                                    weeks="01.12-16.12.2023,17.12-22.12.2023,23.12-30.12.2023")
    assert_value(record_summary.data["product_sum"], 206)

    statement = application_generator.statements[0]
    validate_document_creation(statement, StatementGenerator, "NoDairyContractSchool_Oswiadczenie.docx")
    all_fields_to_marge_are_in_file(statement.generated_documents[0].name,
                                    school_name="NoDairyContractSchool",
                                    school_regon="123456789",
                                    school_nip="1234567890",
                                    school_address="street 123",
                                    date_day="30",
                                    date_month="12",
                                    date_year="2023",
                                    city="City",
                                    week_1="01.12-16.12\n2023",
                                    week_2="17.12-22.12\n2023",
                                    week_3="23.12-30.12\n2023",
                                    is_last="X")
    assert_value(statement.data["apple"], 6)
    assert_value(statement.data["carrot"], 200)
    assert_value(statement.data["pear"], 0)
    assert_value(statement.data["fruitall"], 6)
    assert_value(statement.data["vegall"], 200)
    assert_value(statement.bd.data["kids_no"], 100)

    assert record_summary.data["product_sum"] == (statement.data["fruitall"] + statement.data["vegall"])

    validate_document_creation(application_generator, ApplicationGenerator,
                               "Wniosek_o_pomoc_2_1_2022_2023_warzywa-owoce.docx")
    all_fields_to_marge_are_in_file(application_generator.generated_documents[0].name,
                                    weeks="01.12-16.12.2023,17.12-22.12.2023,23.12-30.12.2023",
                                    app="2/1/2022/2023")

    assert_value(application_generator.data["apple"], 6)
    assert_value(common_data.program["fruitVeg_price"], 1.5, precision=1)
    assert_value(application_generator.data["applewn"], 9.00, precision=2)
    assert_value(application_generator.data["applevat"], 0.00, precision=2)
    assert_value(application_generator.data["applewb"], 9.00, precision=2)
    assert_value(application_generator.data["carrot"], 200)
    assert_value(application_generator.data["carrotwn"], 300.00, precision=2)
    assert_value(application_generator.data["carrotvat"], 24.00, precision=2)
    assert_value(application_generator.data["carrotwb"], 324.00, precision=2)
    assert_value(application_generator.data["pear"], 0)
    assert_value(application_generator.data["fruitall"], 6)
    assert_value(application_generator.data["fruitallwn"], 9.00, precision=2)
    assert_value(application_generator.data["fruitallvat"], 0.00, precision=2)
    assert_value(application_generator.data["fruitallwb"], 9.00, precision=2)
    assert_value(application_generator.data["vegall"], 200)
    assert_value(application_generator.data["vegallwn"], 300.00, precision=2)
    assert_value(application_generator.data["vegallvat"], 24.00, precision=2)
    assert_value(application_generator.data["vegallwb"], 324.00, precision=2)
    assert_value(application_generator.data["kids_no"], 100)
    assert_value(application_generator.data["app_school_no"], 1)
    assert_value(application_generator.data["weeks_no"], 3)
    assert_value(application_generator.data["income"], 333.00, precision=2)
    application.delete_from_db()
