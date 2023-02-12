from auth.accesscontrol import roles_required, AllowedRoles
from resources.company import CompanyResource, CompaniesResource, CompanyRegister
from resources.contracts import ContractsCreateResource, ContractResource, ContractsAllResource, \
    AnnexResource
from resources.product import WeightTypeResource, ProductTypeResource, \
    ProductResource, ProductStoreResource, ProductBoxResource
from resources.program import ProgramResource, ProgramRegister, ProgramsResource
from resources.record import RecordsAllResource, RecordResource, RecordDeliveryCreate
from resources.school import SchoolResource, SchoolRegister, SchoolsResource
from resources.task_progress import TaskProgressStatus
from resources.user import UserResource, User, UserLogin, UserLogout, RefreshToken, Users
from resources.register import RegisterResource
from helpers.google_drive import GoogleDriveCommands
from helpers.json_encoder import to_json
from resources.week import WeekResource, WeekRegister, WeeksResource
from helpers.logger import app_logger

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
    api.add_resource(ProductBoxResource, '/product_box')

    api.add_resource(RecordsAllResource, '/records')
    api.add_resource(RecordResource, '/record/<int:record_id>')
    api.add_resource(RecordDeliveryCreate, '/create_delivery')
    api.add_resource(TaskProgressStatus, '/task_progress/<string:task_id>')

    @app.route("/")
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def main_page():
        return {'message': "You've entered home page"}, 200

    @app.route("/remote_folders_list/<string:google_id>")
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def remote_folders_list(google_id: str):
        res = to_json(GoogleDriveCommands.search(parent_id=google_id))
        return {'remote_folders': res}, 200

    @app.route("/show_logs")
    @roles_required([AllowedRoles.admin.name])
    def show_logs():
        log_res = ""
        with open("rykosystem.log", 'r+') as log_file:
            log_res = log_file.read()
            if log_res:
                app_logger.info(f"{log_res}")
                log_file.truncate(0)
            else:
                return {'message': 'Log file empty'}, 200
        return {'message': f'Log file data: {log_res}'}, 200
