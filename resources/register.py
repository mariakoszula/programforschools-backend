from flask_restful import Resource
from auth.accesscontrol import roles_required, handle_exception_pretty
from models.user import AllowedRoles
from tasks.generate_register_task import queue_register, queue_suppliers_register


class RegisterResource(Resource):

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        try:
            return queue_register(program_id)
        except ValueError as e:
            return {'error': f"{e}"}, 400


class RegisterSuppliersResource(Resource):

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        try:
            return queue_suppliers_register(program_id)
        except ValueError as e:
            return {'error': f"{e}"}, 400
