from db import db


class BaseDatabaseQuery:

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def update_db(self, **update_patch):
        for name, changed_value in update_patch.items():
            if changed_value and hasattr(self, name):
                setattr(self, name, changed_value)
        db.session.commit()

    def json(self):
        return {column.name: getattr(self, column.name, None) for column in self.__table__.columns}

    @classmethod
    def all(cls):
        return cls.query.all()
