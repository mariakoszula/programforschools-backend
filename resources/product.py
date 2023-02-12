from flask import request
from flask_restful import Resource
from marshmallow import fields, Schema, validate
from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from models.base_database_query import ProgramQuerySchema
from models.product import WeightTypeModel, ProductTypeModel, ProductModel, ProductStoreModel, ProductBoxModel


class NameQuerySchema(Schema):
    name = fields.Str(required=True)


class AmountQuerySchema(NameQuerySchema):
    amount = fields.Int(required=True, validate=validate.Range(1, 200))


class ProductQuerySchema(NameQuerySchema):
    product_type = fields.Str(required=True)
    weight_type = fields.Str(required=True)


class ProductStoreQuerySchema(Schema):
    weight = fields.Float(required=False)
    min_amount = fields.Int(required=True)


class ProductStoreQueryPostSchema(ProgramQuerySchema, NameQuerySchema, ProductStoreQuerySchema):
    pass


class ProductStoreByTypeQuerySchema(ProgramQuerySchema):
    product_type = fields.Str(required=True)


name_query = NameQuerySchema()


def validate_body(validator):
    errors = validator.validate(request.json)
    if errors:
        return {'message': f"{errors}"}, 400


def successful_response(model, data):
    return {
               model.__tablename__: data.json()
           }, 200


def simple_post(model, *args, validator=name_query):
    if err := validate_body(validator):
        return err
    filter_data = {'name': request.json["name"]}
    for arg in args:
        filter_data[arg] = request.json[arg]
    found = model.find_by(**filter_data)
    if found:
        return {'message': f"{model.__tablename__} {request.json['name']} already exists"}, 400
    return successful_response(model, model(**request.json))


def simple_get_all(model):
    return {f'{model.__tablename__}': [res.json() for res in model.all()]}, 200


class WeightTypeResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(WeightTypeModel)

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

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all(ProductModel)


class ProductStoreResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(ProductStoreModel, "program_id", validator=ProductStoreQueryPostSchema())

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


class ProductStoreUpdateResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, product_id):
        if err := validate_body(ProductStoreQuerySchema()):
            return err
        try:
            product = ProductStoreModel.find_by_id(product_id)
            product.update_db(**request.json)
            return successful_response(ProductStoreModel, product)
        except ValueError as e:
            return {'message': f'{e}'}, 400


class ProductBoxResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(ProductBoxModel, "amount", validator=AmountQuerySchema())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all(ProductBoxModel)
