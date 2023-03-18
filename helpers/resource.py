from flask import request

from helpers.logger import app_logger
from helpers.schema_validators import name_query, program_schema


def validate_body(validator):
    errors = validator.validate(request.json)
    if errors:
        return {'message': f"{errors}"}, 400


def successful_response(model, data=None, code=201):
    if data is None:
        data = model(**request.json)
    return {
               model.__tablename__: data.json()
           }, code


def simple_post(model, *args, validator=name_query):
    if err := validate_body(validator):
        return err
    filter_data = {}
    for arg in args:
        filter_data[arg] = request.json[arg]
    found = model.find_by(**filter_data)
    if found:
        return {'message': f"{model.__tablename__} '{found}' already exists"}, 400
    return successful_response(model)


def simple_get_all(model):
    return {f'{model.__tablename__}': [res.json() for res in model.all()]}, 200


def simple_get_all_by_program(model, *, _order=None):
    errors = program_schema.validate(request.args)
    if errors:
        return {f'{model.__tablename__}': [],
                "message": f"{errors}"}, 400
    program_id = request.args["program_id"]
    if _order:
        res = model.all_filtered_by_program(program_id).order_by(_order)
    else:
        res = model.all_filtered_by_program(program_id)
    return {f'{model.__tablename__}': [r.json() for r in res]}, 200


def simple_get(model, index):
    found = model.find_by_id(index)
    if not found:
        return {'message': f'{model.__tablename__} {index} does not exists'}, 404
    return successful_response(model, found, code=200)


def put_action(model, index):
    try:
        found = model.find_by_id(index)
        found.update_db(**request.json)
        return successful_response(model, found)
    except ValueError as e:
        return {'message': f'{e}'}, 400


def simple_put(model, index, validator=name_query):
    if err := validate_body(validator):
        return err
    return put_action(model, index)


def simple_delete(model, index):
    found = model.find_by_id(index)
    if not found:
        return {'message': f'{model.__tablename__} {index} does not exists'}, 404
    found.delete_from_db()
    return {'message': f'{model.__tablename__} {index} removed'}, 200


def replace_ids_with_models(model, name):
    if not request.json.get(name):
        return
    res = []
    for arg in request.json[name]:
        try:
            res.append(model.find_by_id(arg))
        except ValueError as e:
            app_logger.warn(f"Failed to replace id with model due to {e}")
    request.json[name] = res
