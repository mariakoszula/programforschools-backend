import pytest

from documents_generator.ApplicationForSchoolGenerator import RecordsSummaryGenerator, get_application_dir_per_school
from documents_generator.ApplicationGenerator import get_application_dir
from models.application import ApplicationModel, ApplicationType
from os import path

from models.contract import AnnexModel
from models.record import RecordModel
from tests.common import all_fields_to_marge_are_in_file, add_record, GoogleDriveFakeCommands


def test_record_summary_generator(contract_for_school_no_dairy, week, second_week, third_week,
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
    AnnexModel(contract_for_school_no_dairy, validity_date="21.12.2023", fruitVeg_products=10)
    add_record("15.12.2023", contract_for_school_no_dairy.id, product_store_fruit)  # 3 kids no
    add_record("30.12.2023", contract_for_school_no_dairy.id, product_store_vegetable)  # 10 kids no
    add_record("18.12.2023", contract_for_school_no_dairy.id, product_store_vegetable)  # 3 kids no
    add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_fruit)  # 10 kids no
    records = RecordModel.filter_records_by_contract(application, contract_for_school_no_dairy)
    record_summary = RecordsSummaryGenerator(application, records, "30.12.2023", _output_dir="tmp",
                                             _drive_tool=GoogleDriveFakeCommands)
    assert record_summary.remote_parent.name == "tmp/NoDairyContractSchool_Ewidencja_dostaw.docx"
    record_summary.generate()
    assert isinstance(record_summary, RecordsSummaryGenerator)
    assert len(record_summary.generated_documents) == 1
    assert path.isdir(record_summary.output_directory)
    assert record_summary.generated_documents[0].name == "tmp/NoDairyContractSchool_Ewidencja_dostaw.docx"
    all_fields_to_marge_are_in_file(record_summary.generated_documents[0].name,
                                    school_name="NoDairyContractSchool",
                                    school_regon="123456789",
                                    school_nip="1234567890",
                                    school_address="street 123",
                                    date_day="30",
                                    date_month="12",
                                    date_year="2023",
                                    city="City",
                                    weeks="01.12.2023-16.12.2023,17.12.2023-22.12.2023,23.12.2023-30.12.2023")
    assert record_summary.product_sum == 26
    application.delete_from_db()
