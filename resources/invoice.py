from flask import request
from flask_restful import Resource
from marshmallow import fields, validate, Schema
from auth.accesscontrol import roles_required, AllowedRoles, handle_exception_pretty
from helpers.resource import simple_post, simple_put, simple_get, simple_delete, simple_get_all, \
    simple_get_all_by_program, validate_body
from helpers.schema_validators import InvoiceQuerySchema, NickWithNameQuery, NickWithNameOptQuery, \
    InvoiceUpdateQuerySchema, InvoiceProductSchema, AmountFloatQuerySchema, InvoiceDisposalSchema
from models.invoice import SupplierModel, InvoiceModel, InvoiceProductModel, InvoiceDisposalModel
from tasks.generate_invoice_disposal_task import queue_invoice_disposal


class SupplierRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(SupplierModel, "name", validator=NickWithNameQuery())


class SupplierResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, supplier_id):
        return simple_put(SupplierModel, supplier_id, validator=NickWithNameOptQuery())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, supplier_id):
        return simple_get(SupplierModel, supplier_id)

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, supplier_id):
        return simple_delete(SupplierModel, supplier_id)


class SuppliersResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all(SupplierModel)


class InvoiceRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(InvoiceModel, "name", "program_id", validator=InvoiceQuerySchema())


class InvoiceResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, invoice_id):
        return simple_put(InvoiceModel, invoice_id, validator=InvoiceUpdateQuerySchema())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, invoice_id):
        return simple_get(InvoiceModel, invoice_id)

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, invoice_id):
        return simple_delete(InvoiceModel, invoice_id)


class InvoicesResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all_by_program(InvoiceModel)


class InvoiceProductRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(InvoiceProductModel, "product_store_id", "invoice_id", validator=InvoiceProductSchema())


class InvoiceProductResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, invoice_product_id):
        return simple_put(InvoiceProductModel, invoice_product_id, validator=AmountFloatQuerySchema())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, invoice_product_id):
        return simple_get(InvoiceProductModel, invoice_product_id)

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, invoice_product_id):
        return simple_delete(InvoiceProductModel, invoice_product_id)


class InvoiceProductsResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all_by_program(InvoiceProductModel)


class InvoiceDisposalRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        return simple_post(InvoiceDisposalModel, validator=InvoiceDisposalSchema())


class InvoiceDisposalResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, invoice_disposal_id):
        return simple_put(InvoiceDisposalModel, invoice_disposal_id, validator=AmountFloatQuerySchema())

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, invoice_disposal_id):
        return simple_get(InvoiceDisposalModel, invoice_disposal_id)

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, invoice_disposal_id):
        return simple_delete(InvoiceDisposalModel, invoice_disposal_id)


class InvoiceDisposalsResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        return simple_get_all_by_program(InvoiceDisposalModel)


class InvoiceDisposalCreateQuerySchema(Schema):
    applications = fields.List(fields.Int(), required=True, allow_none=False)


invoice_disposal_create_query = InvoiceDisposalCreateQuerySchema()


class InvoiceDisposalCreateResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls):
        errors = validate_body(invoice_disposal_create_query)
        if errors:
            return {"message": f"{errors}"}, 400
        return queue_invoice_disposal(request)
