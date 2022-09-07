from typing import List

from flask import request
from flask_restful import Resource, reqparse
from marshmallow import fields

from auth.accesscontrol import roles_required, handle_exception_pretty
from documents_generator.ContractGenerator import ContractGenerator
from models.base_database_query import ProgramQuerySchema
from models.contracts import ContractModel
from models.program import ProgramModel
from models.school import SchoolModel
from models.user import AllowedRoles
from helpers.date_converter import DateConverter
from helpers.logger import app_logger
from marshmallow import exceptions


class DelimitedListField(fields.List):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return value.split(",")
        except AttributeError:
            raise exceptions.ValidationError(
                f"{attr} is not a delimited list it has a non string value {value}."
            )


class ContractQuerySchema(ProgramQuerySchema):
    date = fields.DateTime(format=DateConverter.COMMON_VIEW_DATE_PATTERN, required=True)
    schools_list = DelimitedListField(fields.Str(), required=True, allow_none=False)


contract_query_schema = ContractQuerySchema()


def find_contract(school_id, program_id):
    try:
        program: ProgramModel = ProgramModel.find_by_id(program_id)
        school: SchoolModel = SchoolModel.find_by_id(school_id)
        contract: ContractModel = ContractModel.find(program.id, school.id)
        return contract
    except Exception as e:
        app_logger.error(f"Contract not saved due to {e}")


def update_database(contract, **patch_to_update):
    try:
        if not contract:
            contract = ContractModel(contract.school.id, contract.program)
            contract.save_to_db()
        else:
            contract.update_db(**patch_to_update)
        return contract
    except Exception as e:
        app_logger.error(f"Contract not saved due to {e}")


def get_school_list(schools_input):
    return [int(school_id) for school_id in schools_input.split(",")]


class ContractsCreateResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        errors = contract_query_schema.validate(request.args)
        if errors:
            return {"message": f"{errors}"}, 400
        program_id = request.args["program_id"]
        contracts: List[ContractModel] = []
        for school_id in get_school_list(request.args["schools_list"]):
            contract: ContractModel = find_contract(school_id, program_id)
            results = update_database(contract, validity_date=contract.program.start_date)
            if results:
                contracts.append(results)

        documents_to_upload = []
        try:
            for contract in contracts:
                contract_generator: ContractGenerator = ContractGenerator(contract=contract,
                                                                          date=request.args["date"])
                contract_generator.generate()
                documents_to_upload.extend(contract_generator.generated_documents)
        except TypeError as e:
            return {"message": f"Problem occurred during contract generation {e}"}, 500

        # TODO put documents on google drive links to uploaded documnet return here
        return {'contracts': [contract.json() for contract in contracts],
                'documents': []}, 200


class ContractResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id, school_id):
        contract = find_contract(school_id, program_id)
        if not contract:
            return {'message': f'Contract not found for school: {school_id} and program: {program_id}'}, 400
        return {'contract': contract.json()}, 200

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, program_id, school_id):
        parser = reqparse.RequestParser()
        parser.add_argument('fruitVeg_products',
                            required=False,
                            type=int)
        parser.add_argument('dairy_products',
                            required=False,
                            type=int)
        contract = update_database(contract=find_contract(school_id, program_id),
                                   **parser.parse_args())
        if not contract:
            return {'message': f'Contract not found for school: {school_id} and program: {program_id}'}, 400
        return {'contract': contract.json()}, 200
