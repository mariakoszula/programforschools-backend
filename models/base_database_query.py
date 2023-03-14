from helpers.date_converter import DateConverter
from helpers.db import db


class BaseDatabaseQuery:
    @classmethod
    def find_by_id(cls, _id):
        model = cls.query.filter_by(id=_id).first()
        if not model:
            raise ValueError(f"Data in table '{cls.__tablename__}' with id: '{_id}' does not exist.")
        return model

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def update_db(self, **update_patch):
        for name, changed_value in update_patch.items():
            if "date" in name and isinstance(changed_value, str):
                changed_value = DateConverter.convert_to_date(changed_value)
            if changed_value and hasattr(self, name):
                setattr(self, name, changed_value)
        db.session.commit()

    def json(self):
        return {column.name: getattr(self, column.name, None) for column in self.__table__.columns}

    @classmethod
    def all(cls):
        return cls.query.all()

    @classmethod
    def all_filtered_by_program(cls, program_id):
        return cls.query.filter_by(program_id=program_id)

    @classmethod
    def find_by(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def find_one_by_name(cls, name):
        return cls.query.filter_by(name=name).one()
