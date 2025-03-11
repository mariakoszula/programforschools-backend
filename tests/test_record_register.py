from datetime import datetime
import pytest

from documents_generator.RecordRegisterGenerator import RecordRegisterGenerator
from models.application import ApplicationModel, ApplicationType
from models.record import RecordModel, RecordState
from tests.common import add_record, GoogleDriveFakeCommands, validate_document_creation

def test_record_register(db_session, contract_for_school_no_dairy, second_contract_for_school,
                                         contract_for_school_no_fruit,
                                         week, second_week, third_week,
                                         product_store_apple, product_store_juice, product_store_carrot,
                                         product_store_kohlrabi, product_store_yoghurt, product_store_milk):
    assert week.program_id == second_week.program_id == third_week.program_id

    add_record("15.12.2023", contract_for_school_no_dairy.id, product_store_apple, db=db_session)
    # add_record("30.12.2023", contract_for_school_no_dairy.id, product_store_carrot)
    # add_record("18.12.2023", contract_for_school_no_dairy.id, product_store_apple)
    # # add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_carrot, final_state=RecordState.GENERATION_IN_PROGRESS)
    # add_record("21.12.2023", contract_for_school_no_dairy.id, product_store_carrot)
    # add_record("22.12.2023", contract_for_school_no_dairy.id, product_store_kohlrabi)
    # add_record("16.12.2023", contract_for_school_no_dairy.id, product_store_juice)
    #
    # add_record("02.12.2023", second_contract_for_school.id, product_store_kohlrabi)
    # add_record("17.12.2023", second_contract_for_school.id, product_store_juice)
    # add_record("20.12.2023", second_contract_for_school.id, product_store_juice)
    # add_record("30.12.2023", second_contract_for_school.id, product_store_kohlrabi)
    # add_record("30.12.2023", second_contract_for_school.id, product_store_yoghurt)
    # add_record("02.12.2023", second_contract_for_school.id, product_store_milk)
    # add_record("17.12.2023", second_contract_for_school.id, product_store_yoghurt)
    #
    # add_record("15.12.2023", contract_for_school_no_fruit.id, product_store_milk)
    # add_record("30.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)
    # add_record("18.12.2023", contract_for_school_no_fruit.id, product_store_milk)
    # add_record("21.12.2023", contract_for_school_no_fruit.id, product_store_yoghurt)
    # add_record("22.12.2023", contract_for_school_no_fruit.id, product_store_milk)
    # add_record("16.12.2023", contract_for_school_no_fruit.id, product_store_milk)
    #
    #
    # application = ApplicationModel(second_week.program_id,
    #                                [contract_for_school_no_dairy, second_contract_for_school,
    #                                 contract_for_school_no_fruit],
    #                                [second_week, third_week],
    #                                ApplicationType.DAIRY)
    # application.contracts = [second_contract_for_school, contract_for_school_no_fruit]
    #
    # record_register_gen = RecordRegisterGenerator(week.program, _output_dir="gen", _drive_tool=GoogleDriveFakeCommands)
    # date = datetime.today().strftime('%d-%m-%Y')
    # validate_document_creation(record_register_gen, RecordRegisterGenerator, f"Rejest_wz_{date}.docx")
    # assert len(record_register_gen.record_by_school_and_product) == 19, "Value of expected record in document does not match"
    #

