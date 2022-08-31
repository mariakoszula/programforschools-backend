from flask_restful import Resource
from auth.accesscontrol import roles_required, handle_exception_pretty
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
            register_generator: DocumentGenerator = RegisterGenerator(program)
            register_generator.generate()
        except ValueError as e:
            return {'error': f"{e}"}, 400

        if register_generator and register_generator.generated_documents:
            register_generator.upload_files_to_remote_drive()
            return {
                'documents': register_generator.generated_documents
            }, 200
        return {'message': 'No files created'}, 204

