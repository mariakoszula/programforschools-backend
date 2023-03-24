import pytest

from documents_generator.ApplicationForSchoolGenerator import RecordsSummaryGenerator, get_application_dir_per_school, \
    statement_factory, StatementGenerator
from documents_generator.ApplicationGenerator import get_application_dir
from models.application import ApplicationModel, ApplicationType
from os import path

from models.contract import AnnexModel
from models.record import RecordModel
from tests.common import all_fields_to_marge_are_in_file, add_record, GoogleDriveFakeCommands


def test_application_generator_fruit_veg(contract_for_school_no_dairy, week, second_week, third_week,
                                         product_store_fruit, product_store_vegetable):
    assert week.program_id == second_week.program_id == third_week.program_id
    application = ApplicationModel(week.program_id, [contract_for_school_no_dairy], [week, second_week, third_week],
                                   ApplicationType.FRUIT_VEG)

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
    records = RecordModel.filter_records_by_contract(application, contract_for_school_no_dairy)
    app_date = "30.12.2023"
    record_summary = RecordsSummaryGenerator(application, records, app_date, _output_dir="gen",
                                             _drive_tool=GoogleDriveFakeCommands)
    assert record_summary.remote_parent.name == "gen/NoDairyContractSchool_Ewidencja_dostaw.docx"
    record_summary.generate()
    assert isinstance(record_summary, RecordsSummaryGenerator)
    assert len(record_summary.generated_documents) == 1
    assert path.isdir(record_summary.output_directory)
    assert record_summary.generated_documents[0].name == "gen/NoDairyContractSchool_Ewidencja_dostaw.docx"
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
    assert record_summary.product_sum == 206

    statement = statement_factory(application, records, app_date, start_week=1, _output_dir="gen",
                                  _drive_tool=GoogleDriveFakeCommands)
    statement.generate()
    assert isinstance(statement, StatementGenerator)
    assert len(statement.generated_documents) == 1
    assert path.isdir(statement.output_directory)
    assert statement.generated_documents[0].name == "gen/NoDairyContractSchool_Oswiadczenie.docx"
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

    assert statement.product_dict["apple"] == 6
    assert statement.product_dict["carrot"] == 200
    assert statement.product_dict["pear"] == 0
    assert statement.product_dict["fruitall"] == 6
    assert statement.product_dict["vegall"] == 200
    assert statement.bd.data["kids_no"] == 100

    assert record_summary.product_sum == (statement.product_dict["fruitall"] + statement.product_dict["vegall"])
    application.delete_from_db()
