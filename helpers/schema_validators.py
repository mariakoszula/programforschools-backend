from marshmallow import Schema, fields, validate
from helpers.date_converter import DateConverter
from models.application import ApplicationType


class ProgramQuerySchema(Schema):
    program_id = fields.Int(required=True)


class DateQuerySchema(Schema):
    date = fields.DateTime(format=DateConverter.COMMON_VIEW_DATE_PATTERN, required=True)


class NameQuerySchema(Schema):
    name = fields.Str(required=True)


class NickWithNameQuery(NameQuerySchema):
    nick = fields.Str(required=True)


class NickWithNameOptQuery(Schema):
    name = fields.Str(required=False)
    nick = fields.Str(required=False)


class InvoiceQuerySchema(NameQuerySchema, DateQuerySchema, ProgramQuerySchema):
    supplier_id = fields.Int(required=True)


class InvoiceUpdateQuerySchema(Schema):
    name = fields.Str(required=False)
    date = fields.DateTime(format=DateConverter.COMMON_VIEW_DATE_PATTERN, required=False)


class AmountQuerySchema(NameQuerySchema):
    amount = fields.Int(required=True, validate=validate.Range(1, 200))


class AmountFloatQuerySchema(Schema):
    amount = fields.Float(required=True)


class InvoiceProductSchema(AmountFloatQuerySchema):
    product_store_id = fields.Int(required=True)
    invoice_id = fields.Int(required=True)


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


class ApplicationSchema(ProgramQuerySchema):
    app_type = fields.Int(required=True,
                          validate=validate.Range(ApplicationType.FULL.value, ApplicationType.FRUIT_VEG.value))
    contracts = fields.List(fields.Int(required=True))
    weeks = fields.List(fields.Int(required=True))


class ApplicationUpdateSchema(Schema):
    contracts = fields.List(fields.Int(required=False))
    weeks = fields.List(fields.Int(required=False))


program_schema = ProgramQuerySchema()
name_query = NameQuerySchema()
