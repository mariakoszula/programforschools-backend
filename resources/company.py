from flask_restful import Resource, reqparse

from accesscontrol import roles_required, AllowedRoles
from models.company import CompanyModel


class CompanyRegister(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name',
                        required=True,
                        type=str,
                        help="Company name cannot be blank")
    parser.add_argument('nip',
                        required=True,
                        type=str,
                        help="Company nip cannot be blank")

    parser.add_argument('regon',
                        required=True,
                        type=str,
                        help="Company regon cannot be blank")

    parser.add_argument('address',
                        required=True,
                        type=str,
                        help="Company address cannot be blank")

    parser.add_argument('address_for_documents',
                        required=True,
                        type=str,
                        help="Company address_for_documents cannot be blank")

    @classmethod
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        data = cls.parser.parse_args()
        if CompanyModel.find_by_nip(data["nip"]):
            return {'message': f'Company with nip {data["nip"]} already exists'}, 400
        try:
            company = CompanyModel(**data)
            company.save_to_db()
        except Exception as e:
            return {'message': f'Company not saved due to {e}'}, 500
        return {
                   'id': company.id,
                   'message': f"Added' {company.name}' to database"
               }, 201


class CompanyResource(Resource):
    @classmethod
    def get(cls, company_id):
        company = CompanyModel.find_by_id(company_id)
        if not company:
            return {'message': f'Company {company_id} does not exists'}, 404
        return company.json()


class CompaniesResource(Resource):
        @classmethod
        def get(cls):
            companies = CompanyModel.all()
            if not companies:
                return {'message': 'No companies found'}, 200
            return {'companies': [company.json() for company in companies]}, 200
