from flask import request
from flask_restful import Resource
from marshmallow import fields, Schema
from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from models.base_database_query import ProgramQuerySchema
from models.product import WeightTypeModel, ProductTypeModel, ProductModel, ProductStoreModel


class NameQuerySchema(Schema):
    name = fields.Str(required=True)


class ProductQuerySchema(NameQuerySchema):
    product_type = fields.Str(required=True)
    weight_type = fields.Str(required=True)


class ProductStoreQuerySchema(ProgramQuerySchema, NameQuerySchema):
    weight = fields.Float(required=False)
    min_amount = fields.Int(required=True)


class ProductStoreByTypeQuerySchema(ProgramQuerySchema):
    product_type = fields.Str(required=True)


name_query = NameQuerySchema()


def simple_post(model, *args, validator=name_query):
    errors = validator.validate(request.json)
    if errors:
        return {'message': f"{errors}"}, 400
    filter_data = {'name': request.json["name"]}
    for arg in args:
        filter_data[arg] = request.json[arg]
    found = model.find_by(**filter_data)
    if found:
        return {'message': f"{model.__tablename__} {request.json['name']} already exists"}, 400
    new = model(**request.json)
    new.save_to_db()
    return {
               model.__tablename__: new.json()
           }, 200


def simple_get_all(model):
    return {f'{model.__tablename__}': [res.json() for res in model.all()]}, 200


class WeightTypeResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(WeightTypeModel)


class WeightTypeAllResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all(WeightTypeModel)


class ProductTypeResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(ProductTypeModel)


class ProductTypeAllResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all(ProductTypeModel)


class ProductResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(ProductModel, validator=ProductQuerySchema())


class ProductStoreResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(ProductStoreModel, "program_id", validator=ProductStoreQuerySchema())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        errors = ProductStoreByTypeQuerySchema().validate(request.args)
        if errors:
            return {"message": f"{errors}"}, 400
        return {
                   'products': [r.json() for r in ProductStoreModel.find(program_id=request.args["program_id"],
                                                                         product_type=request.args["product_type"])]
               }, 200
