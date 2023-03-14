from flask import request
from helpers.schema_validators import name_query


def validate_body(validator):
    errors = validator.validate(request.json)
    if errors:
        return {'message': f"{errors}"}, 400


def successful_response(model, data, code=201):
    return {
               model.__tablename__: data.json()
           }, code


def simple_post(model, *args, validator=name_query):
    if err := validate_body(validator):
        return err
    filter_data = {}
    if "name" in request.json:
        filter_data['name'] = request.json["name"]
    for arg in args:
        filter_data[arg] = request.json[arg]
    found = model.find_by(**filter_data)
    if found:
        return {'message': f"{model.__tablename__} '{request.json['name']}' already exists"}, 400
    return successful_response(model, model(**request.json))


def simple_get_all(model):
    return {f'{model.__tablename__}': [res.json() for res in model.all()]}, 200


def simple_get(model, index):
    found = model.find_by_id(index)
    if not found:
        return {'message': f'{model.__tablename__} {index} does not exists'}, 404
    return successful_response(model, found, code=200)


def simple_put(model, index, validator=name_query):
    if err := validate_body(validator):
        return err
    try:
        found = model.find_by_id(index)
        found.update_db(**request.json)
        return successful_response(model, found)
    except ValueError as e:
        return {'message': f'{e}'}, 400


def simple_delete(model, index):
    found = model.find_by_id(index)
    if not found:
        return {'message': f'{model.__tablename__} {index} does not exists'}, 404
    found.delete_from_db()
    return {'message': f'{model.__tablename__} {index} removed'}, 200
