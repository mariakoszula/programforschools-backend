from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.file_folder_creator import DirectoryCreator
from models.application import ApplicationType, ApplicationModel
from models.product import ProductTypeModel
from os import path


def template_postfix(name):
    if name == ApplicationType.FULL:
        return f""
    return f"_{ProductTypeModel.DAIRY_TYPE if name == ApplicationType.DAIRY else ProductTypeModel.fruit_veg_name()}"


def get_application_dir(application: ApplicationModel):
    program_dir = DirectoryCreator.get_main_dir(school_year=application.program.school_year,
                                                semester_no=application.program.semester_no)
    return path.join(program_dir, application.get_dir())


class ApplicationDiaryGenerator(DocumentGenerator):
    def prepare_data(self):
        pass


class ApplicationFruitVegGenerator(DocumentGenerator):
    def prepare_data(self):
        pass


# TODO for FULL application support
class ApplicationGenerator(DocumentGenerator):
    def prepare_data(self):
        pass
