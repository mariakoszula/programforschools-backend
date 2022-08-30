from json import JSONEncoder


class ObjectJsonEncoder(JSONEncoder):
    def default(self, obj):
        return obj.__dict__


def to_json(list_of_objects):
    return [ObjectJsonEncoder().encode(item) for item in list_of_objects]