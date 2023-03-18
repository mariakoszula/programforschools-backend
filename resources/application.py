from flask import request
from flask_restful import Resource

from auth.accesscontrol import handle_exception_pretty, roles_required, AllowedRoles
from helpers.resource import simple_get_all_by_program, replace_ids_with_models, validate_body, \
    successful_response, put_action, simple_delete
from helpers.schema_validators import ApplicationSchema, program_schema, ApplicationUpdateSchema
from models.application import ApplicationModel, ApplicationType
from models.contract import ContractModel
from models.week import WeekModel


class ApplicationRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        try:
            if err := validate_body(ApplicationSchema()):
                return err
            replace_ids_with_models(ContractModel, "contracts")
            replace_ids_with_models(WeekModel, "weeks")
            return successful_response(ApplicationModel)
        except ValueError as e:
            return {'message': f'{e}'}, 400


class ApplicationTypeResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        errors = program_schema.validate(request.args)
        if errors:
            return {f'app_type': [],
                    "message": f"{errors}"}, 400
        return {'app_type': [ApplicationType.convert_to_str(a) for a in
                             ApplicationModel.possible_types(request.args["program_id"])]}, 200


class ApplicationResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, application_id):
        if err := validate_body(ApplicationUpdateSchema()):
            return err
        replace_ids_with_models(ContractModel, "contracts")
        replace_ids_with_models(WeekModel, "weeks")
        return put_action(ApplicationModel, application_id)

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def delete(cls, application_id):
        return simple_delete(ApplicationModel, application_id)


class ApplicationsResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all_by_program(ApplicationModel)
