from helpers.config_parser import config_parser
from helpers.logger import app_logger


def generate_documents(gen, **kwargs):
    try:
        generator = gen(**kwargs)
        generator.generate()
        generator.upload_files_to_remote_drive()
        generator.export_files_to_pdf()
        return [str(document) for document in generator.generated_documents]
    except TypeError as e:
        app_logger.error(f"{gen}: Problem occurred during document generation '{e}'")


#TODO use in all generators if work
def get_output_name(name, *args):
    return config_parser.get('DocNames', name).format(*args)
