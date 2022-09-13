from flask_restful import Resource, reqparse
import copy

from auth.accesscontrol import roles_required, AllowedRoles
from models.school import SchoolModel

_school_parser = reqparse.RequestParser()
_school_parser.add_argument('name',
                            required=False,
                            type=str)
_school_parser.add_argument('address',
                            required=False,
                            type=str)
_school_parser.add_argument('city',
                            required=False,
                            type=str)
_school_parser.add_argument('nip',
                            required=False,
                            type=str)
_school_parser.add_argument('regon',
                            required=False,
                            type=str)
_school_parser.add_argument('email',
                            required=False,
                            type=str)
_school_parser.add_argument('phone',
                            required=False,
                            type=str)
_school_parser.add_argument('responsible_person',
                            required=False,
                            type=str)
_school_parser.add_argument('representative',
                            required=False,
                            type=str)
_school_parser.add_argument('representative_nip',
                            required=False,
                            type=str)
_school_parser.add_argument('representative_regon',
                            required=False,
                            type=str)


class SchoolRegister(Resource):
    parser = copy.deepcopy(_school_parser)
    parser.add_argument('nick',
                        required=True,
                        type=str,
                        help="Nick cannot be blank")

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        data = cls.parser.parse_args()
        try:
            school = SchoolModel(**data)
            school.save_to_db()
        except Exception as e:
            return {'error': f'School not saved due to {e}'}, 500
        return {'school': school.json()}, 201


class SchoolResource(Resource):
    parser = copy.deepcopy(_school_parser)
    parser.add_argument('nick',
                        required=False,
                        type=str)

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, school_id):
        data = cls.parser.parse_args()
        school = SchoolModel.find_by_id(school_id)
        if not school:
            return {'message': f'School {school_id} does not exists'}, 404
        school.update_db(**data)
        return {'school': school.json()}, 200

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, school_id):
        school = SchoolModel.find_by_id(school_id)
        if not school:
            return {'message': f'School {school_id} does not exists'}, 404
        return school.json()

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def delete(cls, school_id):
        school = SchoolModel.find_by_id(school_id)
        if not school:
            return {'message': f'School {school_id} does not exists'}, 404
        school.delete_from_db()
        return {'message': f'School {school_id} removed'}, 200


class SchoolsResource(Resource):

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        schools = SchoolModel.all()
        if not schools:
            return {'message': 'No schools found'}, 200
        return {'schools': [school.json() for school in schools]}, 200
