from helpers.logger import app_logger
from helpers.config_parser import config_parser
from typing import List

EMPTY_FILED = "................................................................"
DOCX_MIME_TYPE = 'application/vnd.google-apps.document'
PDF_MIME_TYPE = 'application/pdf'
DIR_MIME_TYPE = 'application/vnd.google-apps.folder'
GOOGLE_DRIVE_ID = config_parser.get("GoogleDriveConfig", "google_drive_id")
DOCX_EXT = ".docx"
PDF_EXT = ".pdf"


def get_mime_type(mime_type):
    return f"='{mime_type}'"


class FileData:
    def __init__(self, _name, _mime_type=get_mime_type(DOCX_MIME_TYPE), _id=None, _parent_id=GOOGLE_DRIVE_ID,
                 _webViewLink=None):
        self.name = _name
        self.mime_type = _mime_type
        self.id = _id
        self.web_view_link = _webViewLink
        self.parent_id = _parent_id
        super().__init__()

    def __str__(self):
        return f"{self.name}: webViewLink:{self.web_view_link if self.web_view_link else '-'} {id(self)}"

    def __repr__(self):
        return f"FileData(_name={self.name}, _mime_type={self.mime_type}, _id={self.id})"


def file_found(name: str, file_list: List[FileData]):
    return name in [file.name for file in file_list]


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
