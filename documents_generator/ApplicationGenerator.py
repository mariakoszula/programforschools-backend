from documents_generator.DocumentGenerator import DocumentGenerator
from models.application import ApplicationType
from models.product import ProductTypeModel


def template_postfix(name):
    if name == ApplicationType.FULL:
        return f""
    return f"_{ProductTypeModel.DAIRY_TYPE if name == ApplicationType.DAIRY else ProductTypeModel.fruit_veg_name()}"


class ApplicationGenerator(DocumentGenerator):
    pass
