from typing import List

from flask import request
from flask_restful import Resource, reqparse
from marshmallow import fields
from sqlalchemy.exc import SQLAlchemyError

from auth.accesscontrol import roles_required, handle_exception_pretty
from documents_generator.AnnexGenerator import AnnexGenerator
from documents_generator.ContractGenerator import ContractGenerator
from helpers.common import generate_documents
from models.base_database_query import ProgramQuerySchema, DateQuerySchema
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


def get_school_list(schools_input):
    return [int(school_id) for school_id in schools_input.split(",")]


def generate_documents_with_date(gen, **kwargs):
    return generate_documents(gen, date=request.args["date"], **kwargs)


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
            contract = update_contract_in_database(school_id=school_id, program_id=program_id)
            if contract:
                contracts.append(contract)

        uploaded_documents = []
        for contract in contracts:
            uploaded_documents.extend(generate_documents_with_date(gen=ContractGenerator, contract=contract))

        return {'contracts': [contract.json() for contract in contracts],
                'documents': uploaded_documents}, 200


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
        contract = update_contract_in_database(school_id=school_id, program_id=program_id,
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
        return {'contracts': [contract.json()
                              for contract in all_contracts]}, 200


class AnnexResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('no',
                        required=False,
                        type=int)
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
            raise ValueError(f"date: {errors['date']}")
        if data.get("validity_date") and query_args["date"] and \
                DateConverter.convert_to_date(data["validity_date"]) < DateConverter.convert_to_date(
            query_args["date"]):
            raise ValueError(f'validity_date < sign_date')

    @staticmethod
    def validate_product(data):
        if not (data.get("dairy_products") and data.get("fruitVeg_products")):
            raise ValueError(f'dairy_products and fruitVeg_products are required')

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
            annex = None
            AnnexResource.validate_dates(data, request.args)
            contract = AnnexResource.get_contract(contract_id)
            no = data["no"]
            if no:
                annex = AnnexModel.find(no=no, contract_id=contract.id)
            data = dict((filter((lambda elem: elem[1]), data.items())))
            existing_annex_by_date = AnnexModel.find_by_date(validity_date=data["validity_date"], contract_id=contract.id)
            if annex and (not existing_annex_by_date or existing_annex_by_date.no == annex.no):
                annex.update_db(**data)
            elif existing_annex_by_date:
                return {
                    "annex": existing_annex_by_date.json(),
                    "message": f"Annex with {data['validity_date']} already exists with {existing_annex_by_date.no}"
                }, 404
            elif not existing_annex_by_date and not annex:
                AnnexResource.validate_product(data)
                annex = AnnexModel(contract=contract, **data)
                annex.save_to_db()
            return {'annex': annex.json(),
                    'documents': generate_documents_with_date(gen=AnnexGenerator, annex=annex)}, 200
        except ValueError as e:
            return {'message': f"{e}"}, 400
        except Exception as e:
            app_logger.error(f"Annex not saved due to {e}")
            return {'message': f'Could not create annex error: {e}'}, 500
