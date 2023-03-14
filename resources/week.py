from flask_restful import Resource, reqparse, request
from sqlalchemy.exc import SQLAlchemyError
from auth.accesscontrol import roles_required, AllowedRoles
from models.week import WeekModel
from helpers.date_converter import DateConverter
from helpers.schema_validators import program_schema
from helpers.logger import app_logger


class WeekRegister(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('week_no',
                        required=True,
                        type=int,
                        help="Week no cannot be blank format: int.")
    parser.add_argument('start_date',
                        required=True,
                        type=lambda date: DateConverter.convert_to_date(date),
                        help="Start date should be in format DD.MM.YYYY")
    parser.add_argument('end_date',
                        required=True,
                        type=lambda date: DateConverter.convert_to_date(date),
                        help="End date should be in format DD.MM.YYYY")
    parser.add_argument('program_id',
                        required=True,
                        type=int,
                        help="Week id cannot be blank")

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        data = cls.parser.parse_args()
        if WeekModel.find(data["week_no"], data["program_id"]):
            return {
                       'message': f"'Week {data['week_no']} for program {data['program_id']}' already exists"
                   }, 400
        try:
            week = WeekModel(**data)
        except ValueError as e:
            return {'error': f'{e}'}, 400
        except Exception as e:
            return {'error': f'Week not saved due to {e}'}, 500
        return {
                   'week': week.json(),
                   'message': f"Added' {week.week_no} for program {week.program_id} to database"
               }, 201


class WeekResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('week_no',
                        required=False,
                        type=int,
                        help="Week number cannot be blank format: int.")
    parser.add_argument('start_date',
                        required=False,
                        type=lambda date: DateConverter.convert_to_date(date),
                        help="Start date should be in format DD.MM.YYYY")
    parser.add_argument('end_date',
                        required=False,
                        type=lambda date: DateConverter.convert_to_date(date),
                        help="End date should be in format DD.MM.YYYY")

    @classmethod
    def get(cls, week_id):
        week = WeekModel.find_by_id(week_id)
        if not week:
            return {'message': f'Week {week_id} does not exists'}, 404
        return week.json()

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def delete(cls, week_id):
        program = WeekModel.find_by_id(week_id)
        if not program:
            return {'message': f'Week {week_id} does not exists'}, 404
        try:
            program.delete_from_db()
        except SQLAlchemyError as e:
            app_logger.error(f"Error deleting week {week_id} from database: {e}")
            return {'message': f"Cannot remove this week, it is possible records belong already to this week"}, 400
        return {'deleted_week': week_id}, 200

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, week_id):
        data = cls.parser.parse_args()
        week = WeekModel.find_by_id(week_id)
        if not week:
            return {'message': f'Week {week_id} does not exists'}, 404
        if any([value for value in data.values()]):
            week.update_db(**data)
            return {'week': week.json(),
                    'message': f'Week {week_id} updated'}, 200
        return {'message': f'Week {week_id} not updated, nothing to update, validate the request'}, 400


class WeeksResource(Resource):
    @classmethod
    def get(cls):
        errors = program_schema.validate(request.args)
        if errors:
            return {'weeks': [],
                    "message": f"{errors}"}, 400
        program_id = request.args["program_id"]
        weeks = WeekModel.all_filtered_by_program(program_id).order_by(WeekModel.start_date)
        return {'weeks': [week.json() for week in weeks]}, 200
