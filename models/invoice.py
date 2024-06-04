from typing import List

from helpers.date_converter import DateConverter
from models.base_database_query import BaseDatabaseQuery
from helpers.db import db


class SupplierModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'supplier'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    nick = db.Column(db.String(30), nullable=False, unique=True)

    def __init__(self, name, nick):
        self.name = name
        self.nick = nick
        self.save_to_db()

    def __str__(self):
        return f"{self.name} <{self.nick}>"

    def __repr__(self):
        return f"SupplierModel({self.name}, {self.nick})"


class InvoiceModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = db.relationship('SupplierModel', backref=db.backref('invoices', lazy=True))
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel', backref=db.backref('invoices', lazy=True))
    __table_args__ = (db.UniqueConstraint('program_id', 'name'),)

    def __init__(self, name, date, supplier_id, program_id):
        self.name = name
        self.date = DateConverter.convert_to_date(date)
        self.supplier_id = supplier_id
        self.program_id = program_id
        self.save_to_db()

    def __str__(self):
        return f"Invoice '{self.name}' from '{self.supplier.nick}' on {DateConverter.convert_date_to_string(self.date)}"

    def __repr__(self):
        return f"Invoice({self.name}, {self.date}, {self.supplier_id}, {self.program_id})"

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "date")
        return data


class InvoiceProductModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'invoice_product'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    invoice = db.relationship('InvoiceModel', backref=db.backref('products', lazy=True))
    product_store_id = db.Column(db.Integer, db.ForeignKey('product_store.id'), nullable=False)
    product_store = db.relationship('ProductStoreModel', backref=db.backref('invoices', lazy=True))
    amount = db.Column(db.Float, nullable=False)

    __table_args__ = (db.UniqueConstraint('invoice_id', 'product_store_id'),)

    def __init__(self, invoice_id, product_store_id, amount):
        self.invoice_id = invoice_id
        self.product_store_id = product_store_id
        self.amount = amount
        self.save_to_db()

    @classmethod
    def all_filtered_by_program(cls, program_id):
        return cls.query.join(cls.invoice).filter_by(program_id=program_id)

    def __str__(self):
        return f"Numer faktury {self.invoice.name}: " \
               f"{self.product_store.product.name} {self.amount}{self.product_store.product.weight.name}"

    def __repr__(self):
        return f"InvoiceProduct({self.invoice_id}, {self.product_store_id}, {self.amount})"

    @classmethod
    def find_by(cls, product_store_id, invoice_id):
        return cls.query.filter_by(product_store_id=product_store_id).filter_by(invoice_id=invoice_id).first()


class InvoiceDisposalModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'invoice_disposal'
    id = db.Column(db.Integer, primary_key=True)
    invoice_product_id = db.Column(db.Integer, db.ForeignKey('invoice_product.id'), nullable=False)
    invoice_product = db.relationship('InvoiceProductModel', backref=db.backref('invoice_products', lazy=True))
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    application = db.relationship('ApplicationModel', backref=db.backref('applications', lazy=True))
    amount = db.Column(db.Float, nullable=False)

    def __init__(self, invoice_product_id, application_id, amount):
        existing_disposals = InvoiceDisposalModel.query.filter_by(invoice_product_id=invoice_product_id).all()
        existing_disposals_amount = sum(id.amount for id in existing_disposals)
        if existing_disposals and (existing_disposals_amount + int(amount)) > existing_disposals[0].invoice_product.amount:
            raise ValueError(
                "Suma produktów przypisanych do wniosków przekracza sumę na fakturze")

        self.invoice_product_id = invoice_product_id
        self.application_id = application_id
        self.amount = amount
        self.save_to_db()

    def __str__(self):
        return f"Wniosek: {self.application} {self.invoice_product}: {self.amount}"

    def __repr__(self):
        return f"InvoiceDisposalModel({self.invoice_product_id}, {self.application_id}, {self.amount})"

    @classmethod
    def all_filtered_by_program(cls, program_id):
        output = InvoiceDisposalModel.all()
        return list(filter(lambda i: i.invoice_product.invoice.program_id != program_id, output))

    @classmethod
    def all_filtered_by_application(cls, applications: List[int]):
        return cls.query.filter(cls.application_id.in_(applications)).all()
