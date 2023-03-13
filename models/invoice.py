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
    number = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = db.relationship('SupplierModel', backref=db.backref('invoices', lazy=True))
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel', backref=db.backref('invoices', lazy=True))

    def __init__(self, number, date, supplier_id, program_id):
        self.number = number
        self.date = DateConverter.convert_to_date(date)
        self.supplier_id = supplier_id
        self.program_id = program_id
        self.save_to_db()

    def __str__(self):
        return f"Invoice '{self.number}' from '{self.supplier.nick}' on {DateConverter.convert_date_to_string(self.date)}"

    def __repr__(self):
        return f"Invoice({self.number}, {self.date}, {self.supplier_id}, {self.program_id})"


class InvoiceProductModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'invoice_product'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    invoice = db.relationship('InvoiceModel', backref=db.backref('products', lazy=True))
    product_store_id = db.Column(db.Integer, db.ForeignKey('product_store.id'), nullable=False)
    product_store = db.relationship('ProductStoreModel', backref=db.backref('invoices', lazy=True))
    amount = db.Column(db.Integer, nullable=False)

    def __init__(self, invoice_id, product_store_id, amount):
        self.invoice_id = invoice_id
        self.product_store_id = product_store_id
        self.amount = amount
        self.save_to_db()

    def __str__(self):
        return f"InvoiceNo {self.invoice.number}: " \
               f"{self.product_store.product.name} {self.amount}{self.product_store.product.weight.name}"

    def __repr__(self):
        return f"InvoiceProduct({self.invoice_id}, {self.product_store_id}, {self.amount})"
