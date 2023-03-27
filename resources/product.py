from flask import request
from flask_restful import Resource
from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from helpers.schema_validators import ProductQuerySchema, ProductStoreQueryPostSchema, ProductStoreByTypeQuerySchema, \
    ProductStoreQuerySchema, AmountQuerySchema
from models.product import WeightTypeModel, ProductTypeModel, ProductModel, ProductStoreModel, ProductBoxModel
from helpers.resource import simple_get_all, simple_post, simple_put


class WeightTypeResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(WeightTypeModel, "name")

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
        return simple_post(ProductTypeModel, "name")

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
        return simple_post(ProductModel, "name", validator=ProductQuerySchema())

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
        return simple_post(ProductStoreModel, "program_id", "name", validator=ProductStoreQueryPostSchema())

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
        return simple_put(ProductStoreModel, product_id, validator=ProductStoreQuerySchema())


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
