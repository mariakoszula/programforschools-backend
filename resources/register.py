from flask_restful import Resource
from auth.accesscontrol import roles_required, handle_exception_pretty
from helpers.common import generate_documents
from models.user import AllowedRoles
from documents_generator.RegisterGenerator import RegisterGenerator, DocumentGenerator
from models.program import ProgramModel


class RegisterResource(Resource):

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        try:
            program = ProgramModel.find_by_id(program_id)
            return {
                'documents': generate_documents(gen=RegisterGenerator, program=program)
            }, 200
        except ValueError as e:
            return {'error': f"{e}"}, 400
