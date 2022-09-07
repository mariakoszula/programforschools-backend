from flask_restful import Resource, reqparse

from auth.accesscontrol import roles_required, AllowedRoles
from models.program import ProgramModel
from helpers.data_converter import DataConverter
from helpers.file_folder_creator import DirectoryCreator
import copy
from models.directory_tree import DirectoryTreeModel

_program_parser = reqparse.RequestParser()
_program_parser.add_argument('dairy_price',
                             required=False,
                             type=float,
                             help="Dairy price should be in 0.0 format")
_program_parser.add_argument('fruitVeg_price',
                             required=False,
                             type=float,
                             help="FruitVeg price should be in 0.0 format")
_program_parser.add_argument('start_date',
                             required=False,
                             type=lambda date: DataConverter.convert_to_date(date),
                             help="Start date should be in format DD.MM.YYYY")
_program_parser.add_argument('end_date',
                             required=False,
                             type=lambda date: DataConverter.convert_to_date(date),
                             help="End date should be in format DD.MM.YYYY")
_program_parser.add_argument('dairy_min_per_week',
                             required=False,
                             type=int,
                             help="Dairy min per week should be an int format")
_program_parser.add_argument('fruitVeg_min_per_week',
                             required=False,
                             type=int,
                             help="FruitVeg min per week should be an int format")
_program_parser.add_argument('dairy_amount',
                             required=False,
                             type=int,
                             help="Dairy amount should be an int format")
_program_parser.add_argument('fruitVeg_amount',
                             required=False,
                             type=int,
                             help="FruitVeg amount should be an int format")


class ProgramRegister(Resource):
    parser = copy.deepcopy(_program_parser)
    parser.add_argument('semester_no',
                        required=True,
                        type=int,
                        help="Semester number cannot be blank")
    parser.add_argument('school_year',
                        required=True,
                        type=str,
                        help="School year cannot be blank")
    parser.add_argument('company_id',
                        required=True,
                        type=int,
                        help="Company id cannot be blank")

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        data = cls.parser.parse_args()
        if ProgramModel.find(data["school_year"], data["semester_no"]):
            return {
                       'message': f"'Program {data['school_year']} for semester {data['semester_no']}' already exists"
                   }, 400
        try:
            program = ProgramModel(**data)
            program.save_to_db()
            main_directory = DirectoryCreator.create_main_directory_tree(program)
            if not main_directory:
                program.delete_from_db()
                return {'error': f'Program not saved because main directory on google drive was not created'}, 500
            main_directory.save_to_db()
            for directory in DirectoryCreator.create_directory_tree(program, main_directory):
                directory.save_to_db()
        except ValueError as e:
            return {'error': f"{e}"}, 500
        except Exception as e:
            return {'error': f'Program not saved due to {e}'}, 500
        return {
                   'program': program.json(),
                   'directory_tree': [directory.json() for directory in
                                      DirectoryTreeModel.all_filtered_by_program(program_id=program.id)],
               }, 201


class ProgramResource(Resource):
    parser = copy.deepcopy(_program_parser)

    @classmethod
    def get(cls, program_id):
        program = ProgramModel.find_by_id(program_id)
        if not program:
            return {'message': f'Program {program_id} does not exists'}, 404
        return program.json()

    @classmethod
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, program_id):
        program = ProgramModel.find_by_id(program_id)
        if not program:
            return {'message': f'Program {program_id} does not exists'}, 404
        program.delete_from_db()
        return {'message': f'Program {program_id} removed'}, 200

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, program_id):
        data = cls.parser.parse_args()
        program = ProgramModel.find_by_id(program_id)
        if not program:
            return {'message': f'Program {program_id} does not exists'}, 404
        program.update_db(**data)
        return {'program': program.json()}, 200


class ProgramsResource(Resource):
    @classmethod
    def get(cls):
        programs = ProgramModel.all()
        if not programs:
            return {'message': 'No programs found'}, 200
        return {'programs': [program.json() for program in programs]}, 200
