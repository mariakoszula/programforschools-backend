from helpers.logger import app_logger

EMPTY_FILED = "................................................................"



def generate_documents(gen, **kwargs):
    from documents_generator.DocumentGenerator import DocumentGenerator
    generator = gen(**kwargs)
    try:
        DocumentGenerator.generate(generator)
        DocumentGenerator.upload_files_to_remote_drive(generator)
        DocumentGenerator.export_files_to_pdf(generator)
        DocumentGenerator.upload_pdf_files_to_remote_drive(generator)
        return [str(document) for document in generator.generated_documents]
    except TypeError as e:
        app_logger.error(f"{gen}: Problem occurred during document generation '{e}'")


# TODO use in all generators if work
def get_output_name(name, *args):
    from helpers.config_parser import config_parser
    return config_parser.get('DocNames', name).format(*args)


def get_parent_and_children_directories(path_to_file, skip_last=False):
    from os import path
    children = list()
    parent_directory_name = None
    while not parent_directory_name:
        (directories, current) = path.split(path_to_file)
        if not directories or directories in ["/", "\\"]:
            parent_directory_name = current
            break
        children.append(current)
        path_to_file = directories
    if skip_last:
        children = children[1:]
    return parent_directory_name, children[::-1]
