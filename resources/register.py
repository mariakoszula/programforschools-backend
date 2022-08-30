from flask_restful import Resource, request
from accesscontrol import roles_required, handle_exception_pretty
from models.user import AllowedRoles
from documents_generator.RegisterGenerator import RegisterGenerator, DocumentGenerator


class RegisterResource(Resource):

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        register_generator: DocumentGenerator = RegisterGenerator(program_id)
        register_generator.generate()

        if register_generator and register_generator.generated_documents:
            register_generator.upload_files_to_remote_drive()
            return {
                'documents': register_generator.generated_documents
            }, 200
        return {'message': 'No files created'}, 204

