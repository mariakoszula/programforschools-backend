from helpers.db import db
from models.base_database_query import BaseDatabaseQuery


class WeightTypeModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'weight_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)

    def __init__(self, name):
        self.name = name
        self.save_to_db()

    def is_kg(self):
        return self.name.lower() == "KG".lower()

    def json(self):
        return self.name


class ProductTypeModel(db.Model, BaseDatabaseQuery):
    DAIRY_TYPE = "nabiał"
    FRUIT_TYPE = "owoce"
    VEGETABLE_TYPE = "warzywa"

    __tablename__ = 'product_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)

    def __init__(self, name):
        self.name = name
        self.save_to_db()

    def json(self):
        return self.name

    def is_dairy(self):
        return self.name == ProductTypeModel.DAIRY_TYPE

    def is_fruit_veg(self):
        return self.name == ProductTypeModel.FRUIT_TYPE or self.name == ProductTypeModel.VEGETABLE_TYPE

    def get_complementary_type(self):
        if self.name == ProductTypeModel.FRUIT_TYPE:
            return ProductTypeModel.VEGETABLE_TYPE
        if self.name == ProductTypeModel.VEGETABLE_TYPE:
            return ProductTypeModel.FRUIT_TYPE

    @staticmethod
    def dairy_name(replace=False):
        if replace:
            return ProductTypeModel.DAIRY_TYPE.replace("ł", "l")
        return ProductTypeModel.DAIRY_TYPE

    @staticmethod
    def fruit_veg_name():
        return f"{ProductTypeModel.VEGETABLE_TYPE}-{ProductTypeModel.FRUIT_TYPE}"

    def template_name(self):
        base = ""
        if self.name == ProductTypeModel.DAIRY_TYPE:
            base = "dairy"
        if self.name == ProductTypeModel.FRUIT_TYPE:
            base = "fruit"
        if self.name == ProductTypeModel.VEGETABLE_TYPE:
            base = "veg"
        return f"{base}all"


class ProductModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    type = db.relationship('ProductTypeModel',
                           backref=db.backref('product', lazy=True))
    weight_id = db.Column(db.Integer, db.ForeignKey('weight_type.id'), nullable=False)
    weight = db.relationship('WeightTypeModel')
    template_name = db.Column(db.String(80), unique=True, nullable=True)
    vat = db.Column(db.Float, nullable=False, default=0)

    def __init__(self, name, product_type, weight_type, vat=0):
        self.name = name
        self.type_id = ProductTypeModel.find_one_by_name(name=product_type).id
        self.weight_id = WeightTypeModel.find_one_by_name(name=weight_type).id
        self.vat = vat
        self.save_to_db()

    def json(self):
        return {
            'name': self.name,
            'weight_type': self.weight.json(),
            'product_type': self.type.json(),
            'vat': self.vat
        }


class ProductBoxModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'box_with_product'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('ProductModel',
                              backref=db.backref('box', lazy=True))

    def __init__(self, name, amount):
        product = ProductModel.find_one_by_name(name=name)
        self.product_id = product.id
        self.amount = amount
        self.save_to_db()

    def __str__(self):
        return f"{self.product.name} - {self.amount} szt"

    @classmethod
    def find_by(cls, name, amount):
        return cls.query.filter_by(amount=amount).join(cls.product).filter_by(name=name).first()


class ProductStoreModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'product_store'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('ProductModel',
                              backref=db.backref('product_store', lazy=True))
    weight = db.Column(db.Float, nullable=True)
    min_amount = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint('program_id', 'product_id'),)

    def __init__(self, program_id, name, min_amount, weight=0):
        self.program_id = program_id
        self.product_id = ProductModel.find_one_by_name(name).id
        self.min_amount = min_amount
        self.weight = weight
        self.save_to_db()

    def is_min_amount_exceeded(self, nick):
        return [record.contract.school.nick for record in self.records].count(nick) >= self.min_amount

    @classmethod
    def find_by(cls, program_id, name):
        return cls.query.filter_by(program_id=program_id).join(cls.product).filter_by(name=name).first()

    @classmethod
    def find(cls, program_id, product_type):
        product_types = []
        if product_type == ProductTypeModel.fruit_veg_name():
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.FRUIT_TYPE).id)
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.VEGETABLE_TYPE).id)
        else:
            product_types.append(ProductTypeModel.find_one_by_name(product_type).id)
        results = []
        for type_id in product_types:
            results.extend(cls.query.filter_by(program_id=program_id).join(cls.product).filter_by(type_id=type_id).all())
        return results

    def json(self):
        data: {} = super().json()
        data['product'] = self.product.json()
        return data
