from typing import List
from helpers.logger import app_logger
from app import create_app
from models.contract import ContractModel
from tasks.generate_documents_task import create_generator_and_run, queue_task, setup_progress_meta
from documents_generator.ContractGenerator import ContractGenerator
from sqlalchemy.exc import SQLAlchemyError
from models.program import ProgramModel
from models.school import SchoolModel


def find_contract(school_id, program_id):
    try:
        program: ProgramModel = ProgramModel.find_by_id(program_id)
        school: SchoolModel = SchoolModel.find_by_id(school_id)
        contract: ContractModel = ContractModel.find(program.id, school.id)
        return contract
    except Exception as e:
        app_logger.error(f"Contract not saved due to {e}")


def get_school_list(schools_input):
    return [int(school_id) for school_id in schools_input.split(",")]


def update_contract_in_database(school_id, program_id, **patch_to_update):
    try:
        contract: ContractModel = find_contract(school_id, program_id)
        if not contract:
            contract = ContractModel(school_id, ProgramModel.find_by_id(program_id))
            contract.save_to_db()
        else:
            patch_to_update["validity_date"] = contract.program.start_date
            contract.update_db(**patch_to_update)
        return contract
    except SQLAlchemyError as e:
        app_logger.error(f"Contract not saved due to {e}")


async def create_contracts_async(**request):
    with create_app().app_context():
        program_id = request.get("program_id")
        contracts: List[ContractModel] = []
        for school_id in get_school_list(request.get("schools_list")):
            contract = update_contract_in_database(school_id=school_id, program_id=program_id)
            if contract:
                contracts.append(contract)

        input_docs = [(ContractGenerator, {'contract': contract, 'date': request['date']}) for contract in contracts]
        setup_progress_meta(len(input_docs))
        return await create_generator_and_run(input_docs)


def queue_contracts(request):
    return queue_task(func=create_contracts_async, request=request)
