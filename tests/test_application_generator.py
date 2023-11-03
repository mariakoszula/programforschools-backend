import pytest

from documents_generator.ApplicationGenerator import get_application_dir, get_application_dir_per_school, \
    RecordsSummaryGenerator, StatementGenerator, application_factory, ApplicationGenerator
from models.application import ApplicationModel, ApplicationType

from models.contract import AnnexModel
from models.record import RecordModel, RecordState
from tests import common_data
from tests.common import all_fields_to_marge_are_in_file, add_record, GoogleDriveFakeCommands, validate_document_creation


def assert_value(value, expected, precision=0):
    assert f"{value}" == f"{expected:.{precision}f}"


def test_application_generator_fruit_veg(contract_for_school_no_dairy, second_contract_for_school,
                                         contract_for_school_no_fruit,
                                         week, second_week, third_week,
                                         product_store_apple, product_store_juice, product_store_carrot,
                                         product_store_kohlrabi):
    assert week.program_id == second_week.program_id == third_week.program_id
    application = ApplicationModel(week.program_id, [contract_for_school_no_dairy, second_contract_for_school],
                                   [week, second_week, third_week],
                                   ApplicationType.FRUIT_VEG)

    assert get_application_dir(application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_warzywa-owoce"
    assert get_application_dir_per_school(
        application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_warzywa-owoce/EWIDENCJE"
    records = RecordModel.filter_records_by_contract(application, contract_for_school_no_dairy)
    with pytest.raises(ValueError):
        RecordsSummaryGenerator(application, records, "30.12.2023")
    AnnexModel(contract_for_school_no_dairy, validity_date="21.12.2023", fruitVeg_products=100)
    add_record("15.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    add_record("30.12.2023", contract_for_school_no_dairy.id, product_store_carrot)  # 100 kids no
    add_record("18.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_carrot)  # 100 kids no
    add_record("22.12.2023", contract_for_school_no_dairy.id, product_store_kohlrabi)  # 100 kids no
    add_record("16.12.2023", contract_for_school_no_dairy.id, product_store_juice)  # 3 kids no

    AnnexModel(second_contract_for_school, validity_date="01.12.2023", fruitVeg_products=2)
    AnnexModel(second_contract_for_school, validity_date="20.12.2023", fruitVeg_products=11)
    add_record("02.12.2023", second_contract_for_school.id, product_store_kohlrabi)  # 2 kids no
    add_record("17.12.2023", second_contract_for_school.id, product_store_juice)  # 2 kids no
    add_record("20.12.2023", second_contract_for_school.id, product_store_juice)  # 11 kids no
    add_record("30.12.2023", second_contract_for_school.id, product_store_kohlrabi)  # 11 kids no

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
    assert_value(record_summary.data["product_sum"], 309)

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
                                    l="X",
                                    p="",
                                    application_no="1/1/2023/2024")
    assert_value(statement.data["apple"], 6)
    assert_value(statement.data["carrot"], 200)
    assert_value(statement.data["pear"], 0)
    assert_value(statement.data["fruitall"], 9)
    assert_value(statement.data["kohlrabi"], 100)
    assert_value(statement.data["vegall"], 300)
    assert_value(statement.bd[0].data["kids_no"], 100)
    assert record_summary.data["product_sum"] == (statement.data["fruitall"] + statement.data["vegall"])

    second_statement = application_generator.statements[1]
    assert_value(second_statement.bd[0].data["kids_no"], 22)
    assert_value(second_statement.bd[0].data["kids_no_1"], 2)
    assert_value(second_statement.bd[0].data["kids_no_2"], 11)
    assert_value(second_statement.bd[0].data["kids_no_3"], 11)
    assert_value(second_statement.bd[0].maximum_kids_no, 11)

    validate_document_creation(application_generator, ApplicationGenerator,
                               "Wniosek_o_pomoc_1_1_2023_2024_warzywa-owoce.docx")
    all_fields_to_marge_are_in_file(application_generator.generated_documents[0].name,
                                    weeks="01.12-16.12.2023,17.12-22.12.2023,23.12-30.12.2023",
                                    l="X",
                                    p="",
                                    application_no="1/1/2023/2024")

    assert_value(application_generator.data["apple"], 6)
    assert_value(common_data.program["fruitVeg_price"], 1.5, precision=1)
    assert_value(application_generator.data["applewn"], 9.00, precision=2)
    assert_value(application_generator.data["applevat"], 0.00, precision=2)
    assert_value(application_generator.data["applewb"], 9.00, precision=2)
    assert_value(application_generator.data["pear"], 0)
    assert_value(application_generator.data["juice"], 16)
    assert_value(application_generator.data["juicewn"], 24.00, precision=2)
    assert_value(application_generator.data["juicevat"], 0.72, precision=2)
    assert_value(application_generator.data["juicewb"], 24.72, precision=2)
    assert_value(application_generator.data["fruitall"], 22)
    assert_value(application_generator.data["fruitallwn"], 33.00, precision=2)
    assert_value(application_generator.data["fruitallvat"], 0.72, precision=2)
    assert_value(application_generator.data["fruitallwb"], 33.72, precision=2)
    assert_value(application_generator.data["carrot"], 200)
    assert_value(application_generator.data["carrotwn"], 300.00, precision=2)
    assert_value(application_generator.data["carrotvat"], 24.00, precision=2)
    assert_value(application_generator.data["carrotwb"], 324.00, precision=2)
    assert_value(application_generator.data["kohlrabi"], 113)
    assert_value(application_generator.data["kohlrabiwn"], 169.50, precision=2)
    assert_value(application_generator.data["kohlrabivat"], 0.00, precision=2)
    assert_value(application_generator.data["kohlrabiwb"], 169.50, precision=2)
    assert_value(application_generator.data["vegall"], 313)
    assert_value(application_generator.data["vegallwn"], 469.50, precision=2)
    assert_value(application_generator.data["vegallvat"], 24.00, precision=2)
    assert_value(application_generator.data["vegallwb"], 493.50, precision=2)
    assert_value(application_generator.data["kids_no"], 111)
    assert_value(application_generator.data["app_school_no"], 2)
    assert_value(application_generator.data["weeks_no"], 3)
    assert_value(application_generator.data["income"], 527.22, precision=2)
    RecordModel.query.delete()
    AnnexModel.query.delete()
    application.delete_from_db()


def test_consistency_check(contract_for_school_no_dairy, second_contract_for_school,
                           week, second_week, product_store_apple, vegetable):
    application = ApplicationModel(week.program_id, [contract_for_school_no_dairy, second_contract_for_school],
                                   [week, second_week],
                                   ApplicationType.FRUIT_VEG)
    add_record("01.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    add_record("17.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    annex = AnnexModel(contract_for_school_no_dairy, validity_date="17.12.2023", fruitVeg_products=100)

    results = ApplicationGenerator.check_record_consistency(application)
    assert results[0].school == contract_for_school_no_dairy.school
    assert str(results[0].message) == f"17.12.2023: apple  3 -> 100"
    annex.delete_from_db()

    add_record("02.12.2023", second_contract_for_school.id, product_store_apple)  # 22 kids no
    results = ApplicationGenerator.check_record_consistency(application)
    assert results[0].school == second_contract_for_school.school
    assert str(results[0].message) == f"2: 17.12.2023 - 22.12.2023"

    add_record("18.12.2023", second_contract_for_school.id, product_store_apple)
    add_record("03.12.2023", second_contract_for_school.id, product_store_apple, final_state=RecordState.GENERATED)

    results = ApplicationGenerator.check_record_consistency(application)
    assert results[0].school == second_contract_for_school.school
    assert str(results[0].message) == f"03.12.2023: apple  22 != RecordState.DELIVERED"
    application.delete_from_db()


def test_application_generator_with_dairy_contract_school(contract_for_school_no_dairy, second_contract_for_school,
                                                          contract_for_school_no_fruit,
                                                          second_week, third_week,
                                                          product_store_milk, product_store_yoghurt):
    assert second_week.program_id == third_week.program_id
    application = ApplicationModel(second_week.program_id,
                                   [contract_for_school_no_dairy, second_contract_for_school,
                                    contract_for_school_no_fruit],
                                   [second_week, third_week],
                                   ApplicationType.DAIRY)

    assert get_application_dir(application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_nabial"
    assert get_application_dir_per_school(
        application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_nabial/EWIDENCJE"
    records = RecordModel.filter_records_by_contract(application, contract_for_school_no_dairy)
    with pytest.raises(ValueError):
        RecordsSummaryGenerator(application, records, "30.12.2023")
    application.contracts = [second_contract_for_school, contract_for_school_no_fruit]
    AnnexModel(second_contract_for_school, validity_date="21.12.2023", dairy_products=12)

    add_record("30.12.2023", second_contract_for_school.id, product_store_milk)  # 12 kids no
    add_record("18.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 1 kids no
    add_record("21.12.2023", second_contract_for_school.id, product_store_milk)  # 12 kids no
    add_record("22.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 12 kids no

    AnnexModel(contract_for_school_no_fruit, validity_date="29.12.2023", dairy_products=5)
    add_record("29.12.2023", contract_for_school_no_fruit.id, product_store_milk)  # 5 kids no
    add_record("19.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no
    add_record("21.12.2023", contract_for_school_no_fruit.id, product_store_milk)  # 43 kids no
    add_record("23.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no

    app_date = "30.12.2023"
    application_generator = application_factory(application, app_date, start_week=2, is_last=True,
                                                _output_dir="gen", _drive_tool=GoogleDriveFakeCommands)
    record_summary = application_generator.records_summary[0]
    validate_document_creation(record_summary, RecordsSummaryGenerator, "SecondSchool_Ewidencja_dostaw.docx")
    all_fields_to_marge_are_in_file(record_summary.generated_documents[0].name,
                                    school_name="SecondSchoolName",
                                    school_regon="74983579023",
                                    school_nip="098746623",
                                    school_address="street 2",
                                    date_day="30",
                                    date_month="12",
                                    date_year="2023",
                                    city="CitySecond",
                                    weeks="17.12-22.12.2023,23.12-30.12.2023")
    assert_value(record_summary.data["product_sum"], 37)

    statement = application_generator.statements[1]
    validate_document_creation(statement, StatementGenerator, "NoFruitInSchool_Oswiadczenie.docx")
    all_fields_to_marge_are_in_file(statement.generated_documents[0].name,
                                    school_name="NoFruitInSchoolName",
                                    school_regon="yyyyyyyyy",
                                    school_nip="xxxxxxxxx",
                                    school_address="ssssssssss",
                                    date_day="30",
                                    date_month="12",
                                    date_year="2023",
                                    city="NoFruitCity",
                                    week_2="17.12-22.12\n2023",
                                    week_3="23.12-30.12\n2023",
                                    is_last="X",
                                    application_no="1/1/2023/2024")
    assert_value(statement.data["milk"], 48)
    assert_value(statement.data["yoghurt"], 86)
    assert_value(statement.data["kefir"], 0)
    assert_value(statement.data["cheese"], 0)
    assert_value(statement.data["dairyall"], 134)
    assert_value(statement.bd[0].data["kids_no"], 43)

    validate_document_creation(application_generator, ApplicationGenerator,
                               "Wniosek_o_pomoc_1_1_2023_2024_nabial.docx")
    all_fields_to_marge_are_in_file(application_generator.generated_documents[0].name,
                                    weeks="17.12-22.12.2023,23.12-30.12.2023",
                                    application_no="1/1/2023/2024")

    assert_value(application_generator.data["milk"], 72)
    assert_value(common_data.program["dairy_price"], 2.0, precision=1)
    assert_value(application_generator.data["milkwn"], 144.00, precision=2)
    assert_value(application_generator.data["milkvat"], 0.00, precision=2)
    assert_value(application_generator.data["milkwb"], 144.00, precision=2)

    assert_value(application_generator.data["yoghurt"], 99)
    assert_value(application_generator.data["yoghurtwn"], 198.00, precision=2)
    assert_value(application_generator.data["yoghurtvat"], 3.96, precision=2)
    assert_value(application_generator.data["yoghurtwb"], 201.96, precision=2)

    assert_value(application_generator.data["dairyall"], 171)
    assert_value(application_generator.data["dairyallwn"], 342.00, precision=2)
    assert_value(application_generator.data["dairyallvat"], 3.96, precision=2)
    assert_value(application_generator.data["dairyallwb"], 345.96, precision=2)

    assert_value(application_generator.data["kids_no"], 55)
    assert_value(application_generator.data["app_school_no"], 2)
    assert_value(application_generator.data["weeks_no"], 2)

    assert_value(application_generator.data["income"], 345.96, precision=2)

    RecordModel.query.delete()
    AnnexModel.query.delete()
    application.delete_from_db()


def test_application_generator_full(contract_for_school_no_dairy, second_contract_for_school,
                                    contract_for_school_no_fruit,
                                    week, second_week, third_week,
                                    product_store_apple, product_store_juice, product_store_carrot,
                                    product_store_kohlrabi, product_store_milk, product_store_yoghurt):
    application = ApplicationModel(week.program_id, [contract_for_school_no_dairy, second_contract_for_school,
                                                     contract_for_school_no_fruit],
                                   [week, second_week, third_week],
                                   ApplicationType.FULL)
    assert get_application_dir(application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_nabial_i_warzywa-owoce"
    assert get_application_dir_per_school(
        application) == "TEST_PROGRAM_2023_2024_SEMESTR_1/WNIOSKI/1_1_2023_2024_nabial_i_warzywa-owoce/EWIDENCJE"
    AnnexModel(contract_for_school_no_dairy, validity_date="21.12.2023", fruitVeg_products=100)
    add_record("15.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    add_record("30.12.2023", contract_for_school_no_dairy.id, product_store_carrot)  # 100 kids no
    add_record("18.12.2023", contract_for_school_no_dairy.id, product_store_apple)  # 3 kids no
    add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_carrot)  # 100 kids no
    add_record("22.12.2023", contract_for_school_no_dairy.id, product_store_kohlrabi)  # 100 kids no
    add_record("16.12.2023", contract_for_school_no_dairy.id, product_store_juice)  # 3 kids no
    AnnexModel(second_contract_for_school, validity_date="01.12.2023", fruitVeg_products=2)
    AnnexModel(second_contract_for_school, validity_date="20.12.2023", fruitVeg_products=11)
    add_record("02.12.2023", second_contract_for_school.id, product_store_kohlrabi)  # 2 kids no
    add_record("17.12.2023", second_contract_for_school.id, product_store_juice)  # 2 kids no
    add_record("20.12.2023", second_contract_for_school.id, product_store_juice)  # 11 kids no
    add_record("30.12.2023", second_contract_for_school.id, product_store_kohlrabi)  # 11 kids no
    AnnexModel(second_contract_for_school, validity_date="21.12.2023", dairy_products=12)
    add_record("30.12.2023", second_contract_for_school.id, product_store_milk)  # 12 kids no
    add_record("18.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 1 kids no
    add_record("21.12.2023", second_contract_for_school.id, product_store_milk)  # 12 kids no
    add_record("22.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 12 kids no
    add_record("16.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 1 kids no
    add_record("17.12.2023", second_contract_for_school.id, product_store_yoghurt)  # 1 kids no

    AnnexModel(contract_for_school_no_fruit, validity_date="29.12.2023", dairy_products=5)
    add_record("29.12.2023", contract_for_school_no_fruit.id, product_store_milk)  # 5 kids no
    add_record("19.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no
    add_record("21.12.2023", contract_for_school_no_fruit.id, product_store_milk)  # 43 kids no
    add_record("23.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no
    add_record("16.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no
    add_record("17.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)  # 43 kids no

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
    assert_value(record_summary.data["fv_product_sum"], 309)

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
                                    is_last="X",
                                    application_no="1/1/2023/2024")
    assert_value(statement.data["apple"], 6)
    assert_value(statement.data["carrot"], 200)
    assert_value(statement.data["pear"], 0)
    assert_value(statement.data["fruitall"], 9)
    assert_value(statement.data["kohlrabi"], 100)
    assert_value(statement.data["vegall"], 300)
    assert_value(statement.data["dairyall"], 0)
    assert_value(statement.data["milk"], 0)
    assert_value(statement.data["yoghurt"], 0)
    assert_value(statement.bd[0].data["fv_kids_no"], 100)
    assert record_summary.data["fv_product_sum"] == (statement.data["fruitall"] + statement.data["vegall"])

    second_statement = application_generator.statements[1]
    validate_document_creation(second_statement, StatementGenerator, "SecondSchool_Oswiadczenie.docx")

    record_summary_second = application_generator.records_summary[1]
    validate_document_creation(record_summary_second, RecordsSummaryGenerator, "SecondSchool_Ewidencja_dostaw.docx")
    assert_value(second_statement.data["apple"], 0)
    assert_value(second_statement.data["carrot"], 0)
    assert_value(second_statement.data["kohlrabi"], 13)
    assert_value(second_statement.data["juice"], 13)
    assert_value(second_statement.bd[0].data["fv_kids_no"], 22)
    assert_value(second_statement.bd[0].data["fv_kids_no_1"], 2)
    assert_value(second_statement.bd[0].data["fv_kids_no_2"], 11)
    assert_value(second_statement.bd[0].data["fv_kids_no_3"], 11)
    assert_value(second_statement.bd[0].maximum_kids_no, 11)

    validate_document_creation(application_generator, ApplicationGenerator,
                               "Wniosek_o_pomoc_1_1_2023_2024_nabial_i_warzywa-owoce.docx")
    all_fields_to_marge_are_in_file(application_generator.generated_documents[0].name,
                                    weeks="01.12-16.12.2023,17.12-22.12.2023,23.12-30.12.2023",
                                    is_last="X",
                                    application_no="1/1/2023/2024")

    assert_value(application_generator.data["apple"], 6)
    assert_value(common_data.program["fruitVeg_price"], 1.5, precision=1)
    assert_value(application_generator.data["applewn"], 9.00, precision=2)
    assert_value(application_generator.data["applevat"], 0.00, precision=2)
    assert_value(application_generator.data["applewb"], 9.00, precision=2)
    assert_value(application_generator.data["pear"], 0)
    assert_value(application_generator.data["juice"], 16)
    assert_value(application_generator.data["juicewn"], 24.00, precision=2)
    assert_value(application_generator.data["juicevat"], 0.72, precision=2)
    assert_value(application_generator.data["juicewb"], 24.72, precision=2)
    assert_value(application_generator.data["fruitall"], 22)
    assert_value(application_generator.data["fruitallwn"], 33.00, precision=2)
    assert_value(application_generator.data["fruitallvat"], 0.72, precision=2)
    assert_value(application_generator.data["fruitallwb"], 33.72, precision=2)
    assert_value(application_generator.data["carrot"], 200)
    assert_value(application_generator.data["carrotwn"], 300.00, precision=2)
    assert_value(application_generator.data["carrotvat"], 24.00, precision=2)
    assert_value(application_generator.data["carrotwb"], 324.00, precision=2)
    assert_value(application_generator.data["kohlrabi"], 113)
    assert_value(application_generator.data["kohlrabiwn"], 169.50, precision=2)
    assert_value(application_generator.data["kohlrabivat"], 0.00, precision=2)
    assert_value(application_generator.data["kohlrabiwb"], 169.50, precision=2)
    assert_value(application_generator.data["vegall"], 313)
    assert_value(application_generator.data["vegallwn"], 469.50, precision=2)
    assert_value(application_generator.data["vegallvat"], 24.00, precision=2)
    assert_value(application_generator.data["vegallwb"], 493.50, precision=2)
    assert_value(application_generator.data["fv_kids_no"], 111)
    assert_value(application_generator.data["fv_app_school_no"], 2)
    assert_value(application_generator.data["weeks_no"], 3)
    assert_value(application_generator.data["fv_income"], 527.22, precision=2)
    assert_value(application_generator.data["milk"], 72)
    assert_value(common_data.program["dairy_price"], 2.0, precision=1)
    assert_value(application_generator.data["milkwn"], 144.00, precision=2)
    assert_value(application_generator.data["milkvat"], 0.00, precision=2)
    assert_value(application_generator.data["milkwb"], 144.00, precision=2)
    assert_value(application_generator.data["yoghurt"], 187)
    assert_value(application_generator.data["yoghurtwn"], 374.00, precision=2)
    assert_value(application_generator.data["yoghurtvat"], 7.48, precision=2)
    assert_value(application_generator.data["yoghurtwb"], 381.48, precision=2)
    assert_value(application_generator.data["dairyall"], 259)
    assert_value(application_generator.data["dairyallwn"], 518.00, precision=2)
    assert_value(application_generator.data["dairyallvat"], 7.48, precision=2)
    assert_value(application_generator.data["dairyallwb"], 525.48, precision=2)
    assert_value(application_generator.data["kids_no"], 55)
    assert_value(application_generator.data["app_school_no"], 2)
    assert_value(application_generator.data["weeks_no"], 3)
    assert_value(application_generator.data["income"], 525.48, precision=2)
    assert_value(application_generator.data["max_app_school_no"], 3)

    RecordModel.query.delete()
    AnnexModel.query.delete()
    application.delete_from_db()
