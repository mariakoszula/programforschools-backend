import pytest
from models.school import SchoolModel
from models.contracts import ContractModel
from tests.common_data import school_data


@pytest.fixture
def contract_for_school(initial_program_setup):
    school = SchoolModel(**school_data)
    school.save_to_db()
    contract = ContractModel(school.id, initial_program_setup)
    contract.save_to_db()
    yield contract


def test_school_model_with_contract(initial_program_setup, contract_for_school):
    contract = ContractModel.find(contract_for_school.program_id, contract_for_school.school_id)
    assert contract is not None and contract.school.nick == school_data["nick"] \
           and contract.contract_no == "1"


def test_record_model(initial_program_setup):
    pass
