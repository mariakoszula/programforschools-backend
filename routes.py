from auth.accesscontrol import roles_required, AllowedRoles
from helpers.file_folder_creator import DirectoryCreator
from models.directory_tree import DirectoryTreeModel
from models.program import ProgramModel
from resources.application import ApplicationRegister, ApplicationResource, ApplicationsResource, \
    ApplicationTypeResource, validate_application_impl, create_application_impl
from resources.company import CompanyResource, CompaniesResource, CompanyRegister
from resources.contracts import ContractsCreateResource, ContractResource, ContractsAllResource, \
    AnnexResource
from resources.invoice import SupplierResource, SupplierRegister, SuppliersResource, InvoiceResource, InvoiceRegister, \
    InvoiceProductsResource, InvoiceProductResource, InvoiceProductRegister, InvoicesResource
from resources.product import WeightTypeResource, ProductTypeResource, \
    ProductResource, ProductStoreResource, ProductBoxResource, ProductStoreUpdateResource
from resources.program import ProgramResource, ProgramRegister, ProgramsResource
from resources.record import RecordsAllResource, RecordResource, RecordDeliveryCreate, SummarizeDeliveryCreate
from resources.school import SchoolResource, SchoolRegister, SchoolsResource
from resources.task_progress import TaskProgressStatus
from resources.user import UserResource, User, UserLogin, UserLogout, RefreshToken, Users
from resources.register import RegisterResource
from helpers.google_drive import GoogleDriveCommands
from helpers.json_encoder import to_json
from resources.week import WeekResource, WeekRegister, WeeksResource
from helpers.logger import app_logger, LOG_FILE
from helpers.common import get_mime_type, DOCX_MIME_TYPE, PDF_MIME_TYPE
from flask_restful import Api
from flask_cors import CORS


def create_routes(app):
    api = Api(app)
    CORS(app)

    api.add_resource(UserResource, '/register')
    api.add_resource(User, '/user/<int:user_id>')
    api.add_resource(Users, '/users')
    api.add_resource(UserLogin, '/login')
    api.add_resource(UserLogout, '/logout')
    api.add_resource(RefreshToken, '/refresh')

    api.add_resource(CompanyResource, '/company/<int:company_id>')
    api.add_resource(CompanyRegister, '/company')
    api.add_resource(CompaniesResource, '/company/all')

    api.add_resource(ProgramResource, '/program/<int:program_id>')
    api.add_resource(ProgramRegister, '/program')
    api.add_resource(ProgramsResource, '/program/all')

    api.add_resource(WeekResource, '/week/<int:week_id>')
    api.add_resource(WeekRegister, '/week')
    api.add_resource(WeeksResource, '/week/all')

    api.add_resource(SchoolResource, '/school/<int:school_id>')
    api.add_resource(SchoolRegister, '/school')
    api.add_resource(SchoolsResource, '/school/all')

    api.add_resource(RegisterResource, '/create_school_register/<int:program_id>')

    api.add_resource(ContractsCreateResource, '/create_contracts')
    api.add_resource(ContractResource, '/contract/<int:program_id>/<int:school_id>')
    api.add_resource(ContractsAllResource, '/contracts/<int:program_id>/all')
    api.add_resource(AnnexResource, '/annex/<int:contract_id>')

    api.add_resource(WeightTypeResource, '/weight_type')
    api.add_resource(ProductTypeResource, '/product_type')
    api.add_resource(ProductResource, '/product')
    api.add_resource(ProductStoreResource, '/product_store')
    api.add_resource(ProductStoreUpdateResource, '/product_store/<int:product_id>')
    api.add_resource(ProductBoxResource, '/product_box')

    api.add_resource(RecordsAllResource, '/records')
    api.add_resource(RecordResource, '/record/<int:record_id>')
    api.add_resource(RecordDeliveryCreate, '/create_delivery')
    api.add_resource(SummarizeDeliveryCreate, '/summarize_week_delivery/<int:week_id>')

    api.add_resource(SupplierResource, '/supplier/<int:supplier_id>')
    api.add_resource(SupplierRegister, '/supplier')
    api.add_resource(SuppliersResource, '/supplier/all')

    api.add_resource(InvoiceResource, '/invoice/<int:invoice_id>')
    api.add_resource(InvoiceRegister, '/invoice')
    api.add_resource(InvoicesResource, '/invoice/all')

    api.add_resource(InvoiceProductResource, '/invoice_product/<int:invoice_product_id>')
    api.add_resource(InvoiceProductRegister, '/invoice_product')
    api.add_resource(InvoiceProductsResource, '/invoice_product/all')

    api.add_resource(ApplicationRegister, '/application')
    api.add_resource(ApplicationTypeResource, '/application/type')
    api.add_resource(ApplicationResource, '/application/<int:application_id>')
    api.add_resource(ApplicationsResource, '/application/all')

    api.add_resource(TaskProgressStatus, '/task_progress/<string:task_id>')

    @app.route("/validate_application/<int:application_id>")
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def validate_application(application_id):
        return validate_application_impl(application_id)

    @app.route("/create_application/<int:application_id>", methods=['PUT'])
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def create_application(application_id):
        return create_application_impl(application_id)

    @app.route("/")
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def main_page():
        return {'message': "You've entered home page"}, 200

    @app.route("/remote_folders_list/<string:google_id>")
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def remote_folders_list(google_id: str):
        res = to_json(GoogleDriveCommands.search(parent_id=google_id))
        res.append(to_json(GoogleDriveCommands.search(parent_id=google_id,
                                                      mime_type_query=get_mime_type(DOCX_MIME_TYPE))))
        res.append(to_json(GoogleDriveCommands.search(parent_id=google_id,
                                                      mime_type_query=get_mime_type(PDF_MIME_TYPE))))
        return {'remote_folders': res}, 200

    @app.route("/remove_from_google_drive/<string:google_id>")
    @roles_required([AllowedRoles.admin.name])
    def remove_from_google_drive(google_id: str):
        try:
            GoogleDriveCommands.remove(google_id)
        except ValueError as e:
            return {'message': f'{e}'}, 400
        return {'message': f'Removed {google_id} from google drive'}, 200

    @app.route("/create_remote_directory_tree/<int:program_id>")
    @roles_required([AllowedRoles.admin.name])
    def create_remote_directory_tree(program_id: int):
        program = ProgramModel.find_by_id(program_id)
        if not program:
            return {'error': f'Program with {program_id} not found'}, 500
        main_directory = DirectoryCreator.create_main_directory_tree(program)
        if not main_directory:
            return {'error': f'Main directory on google drive was not created see the logs'}, 500
        main_directory.save_to_db()
        for directory in DirectoryCreator.create_directory_tree(program, main_directory):
            directory.save_to_db()
        return {
                   'program': program.json(),
                   'directory_tree': [directory.json() for directory in
                                      DirectoryTreeModel.all_filtered_by_program(program_id=program.id)],
               }, 201

    @app.route("/show_logs")
    @roles_required([AllowedRoles.admin.name])
    def show_logs():
        log_res = ""
        with open(LOG_FILE, 'r+') as log_file:
            log_res = log_file.read()
            if log_res:
                app_logger.info(f"{log_res}")
                log_file.truncate(0)
            else:
                return {'message': 'Log file empty'}, 200
        return {'message': f'Log file data: {log_res}'}, 200
