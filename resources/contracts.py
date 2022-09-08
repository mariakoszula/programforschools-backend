from typing import List

from flask import request
from flask_restful import Resource, reqparse
from marshmallow import fields, Schema

from auth.accesscontrol import roles_required, handle_exception_pretty
from documents_generator.ContractGenerator import ContractGenerator
from models.base_database_query import ProgramQuerySchema
from models.contracts import ContractModel, AnnexModel
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


class DateQuerySchema(Schema):
    date = fields.DateTime(format=DateConverter.COMMON_VIEW_DATE_PATTERN, required=True)


class ContractQuerySchema(ProgramQuerySchema, DateQuerySchema):
    schools_list = DelimitedListField(fields.Str(), required=True, allow_none=False)


contract_query = ContractQuerySchema()
date_query = DateQuerySchema()


def find_contract(school_id, program_id):
    try:
        program: ProgramModel = ProgramModel.find_by_id(program_id)
        school: SchoolModel = SchoolModel.find_by_id(school_id)
        contract: ContractModel = ContractModel.find(program.id, school.id)
        return contract
    except Exception as e:
        app_logger.error(f"Contract not saved due to {e}")


def update_contract_in_database(contract, **patch_to_update):
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
        errors = contract_query.validate(request.args)
        if errors:
            return {"message": f"{errors}"}, 400
        program_id = request.args["program_id"]
        contracts: List[ContractModel] = []
        for school_id in get_school_list(request.args["schools_list"]):
            contract: ContractModel = find_contract(school_id, program_id)
            data_to_update = {}
            if contract:
                data_to_update["validity_date"]=contract.program.start_date
            results = update_contract_in_database(contract, **data_to_update)
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
        contract = update_contract_in_database(contract=find_contract(school_id, program_id),
                                               **parser.parse_args())
        if not contract:
            return {'message': f'Contract not found for school: {school_id} and program: {program_id}'}, 400
        return {'contract': contract.json()}, 200


class ContractsAllResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        all_contracts = ContractModel.all_filtered_by_program(program_id)
        return {'contracts': [contract.json() for contract in all_contracts]}, 200


class AnnexResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('fruitVeg_products',
                        required=False,
                        type=int)
    parser.add_argument('dairy_products',
                        required=False,
                        type=int)
    parser.add_argument('validity_date',
                        required=True,
                        type=lambda date: DateConverter.convert_to_date(date))

    @staticmethod
    def validate_dates(data, query_args):
        errors = date_query.validate(query_args)
        if errors:
            raise ValueError(f"{errors}")
        if data.get("validity_date") and query_args["date"] and data["validity_date"] < query_args["date"]:
            raise ValueError(f'validity_date < sign_date')

    @staticmethod
    def validate_product(data):
        if not data.get("dairy_products") and not data.get("fruitVeg_products"):
            raise ValueError(f'One of two is required: dairy_products or fruitVeg_products')

    @staticmethod
    def get_contract(contract_id):
        contract = ContractModel.find_by_id(contract_id)
        if not contract:
            raise ValueError(f'Contract with {contract_id} id not found.')
        return contract

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, contract_id):
        try:
            contract = AnnexResource.get_contract(contract_id)
            return {'annex': [annex.json() for annex in contract.annex]}, 200
        except ValueError as e:
            return {'message': e}, 400

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, contract_id):
        data = AnnexResource.parser.parse_args()
        try:
            AnnexResource.validate_dates(data, request.args)
            contract = AnnexResource.get_contract(contract_id)
            annex = AnnexModel.find(validity_date=data["validity_date"], contract_id=contract.id)
            data = dict((filter((lambda elem: elem[1]), data.items())))
            if not annex:
                AnnexResource.validate_product()
                annex = AnnexModel(contract=contract, **data)
                annex.save_to_db()
            else:
                annex.update_db(**data)
            # TODO generate documents and upload; annex link
            return {'annex': annex.json(),
                    'documents': ''}, 200
        except ValueError as e:
            return {'message': e}, 400
        except Exception as e:
            app_logger.error(f"Annex not saved due to {e}")
            return {'message': f'Could not create annex error: {e}'}, 500