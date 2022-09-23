from helpers.file_folder_creator import DirectoryCreator
from helpers.logger import app_logger
from mailmerge import MailMerge
from abc import ABC, abstractmethod
from shutil import copy
from os import path, makedirs, remove, rename
from typing import List
from helpers.google_drive import GoogleDriveCommands, DOCX_MIME_TYPE, PDF_MIME_TYPE, FileData
from models.directory_tree import DirectoryTreeModel

DOCX_EXT = ".docx"
PDF_EXT = ".pdf"


class DocumentGenerator(ABC):
    PDF_GENERATION_TRIES = 5

    def __init__(self, template_document, output_directory, output_name):
        if not path.exists(template_document):
            app_logger.error("[%s] template document: %s does not exists", __class__.__name__, template_document)
        self.generated_documents: List[FileData] = []
        self.output_directory = output_directory
        self.output_doc_name = output_name

        self.template_document = template_document
        self._document = self.__start_doc_gen()
        self.__fields_to_merge = self._document.get_merge_fields()

        super(DocumentGenerator, self).__init__()

    def generate(self) -> None:
        self.prepare_data()
        file = path.join(self.output_directory, self.output_doc_name)
        try:
            self.__end_doc_gen(file)
        except ValueError as e:
            app_logger.error("Problem occurred during generating document. [%s]", e)

    @staticmethod
    def copy_to_path(source, dest):
        old_file_name = path.basename(source)
        new_file_name = path.basename(dest)
        new_dst = path.dirname(dest)
        if not path.exists(new_dst):
            makedirs(new_dst)
        if source:
            if path.exists(path.join(dest)):
                remove(path.join(dest))
            copy(source, new_dst)
            rename(path.join(new_dst, old_file_name), path.join(new_dst, new_file_name))

    @staticmethod
    def create_directory(output_directory):
        if not path.exists(output_directory):
            makedirs(output_directory)
            app_logger.debug("[%s] Created new output directory: %s", __class__.__name__, output_directory)
        DirectoryCreator.create_remote_tree(output_directory)

    def __start_doc_gen(self):
        DocumentGenerator.create_directory(self.output_directory)
        return MailMerge(self.template_document)

    def __end_doc_gen(self, generated_file):
        self._document.write(generated_file)
        if not path.exists(generated_file):
            ValueError(f"Document not generated: {generated_file}")
        self.generated_documents.append(FileData(_name=generated_file, _mime_type=DOCX_MIME_TYPE))
        app_logger.debug("[%s] Created new output file: %s", __class__.__name__, generated_file, )

    @abstractmethod
    def prepare_data(self):
        pass

    def upload_files_to_remote_drive(self, file_type=DOCX_EXT):
        # TODO uploaded_file_id does not exists -> retry (3 times or sth)
        # use specified folder id stored in database based on DirectoryTree model and path_to_file
        files = list(filter(lambda file: file_type in file.name, self.generated_documents))
        for index, file_data in enumerate(files):
            parent_dir = DirectoryTreeModel.get_google_parent_directory(file_data.name)
            uploaded_file_id, web_link = GoogleDriveCommands.upload_file(path_to_file=file_data.name,
                                                                         mime_type=file_data.mime_type,
                                                                         parent_id=parent_dir.google_id)
            if uploaded_file_id:
                self.generated_documents[index].id = uploaded_file_id
                self.generated_documents[index].web_view_link = web_link
                app_logger.info(
                    f"File '{file_data.name}' successfully uploaded with id {uploaded_file_id} to "
                    f"{parent_dir}")
            else:
                app_logger.error(f"Failed to upload file '{file_data.name}' to {parent_dir}")

    def export_files_to_pdf(self):
        files = list(filter(lambda file: DOCX_EXT in file.name, self.generated_documents))
        file_data: FileData
        for file_data in files:
            self.generated_documents.append(
                FileData(_name=DocumentGenerator.export_to_pdf(file_data.name, file_data.id),
                         _mime_type=PDF_MIME_TYPE))
        self.upload_files_to_remote_drive(file_type=PDF_EXT)

    @staticmethod
    def export_to_pdf(file_name, source_file_id):
        file_content = GoogleDriveCommands.export_to_pdf(source_file_id)
        pdf_name = file_name.replace(DOCX_EXT, PDF_EXT)
        with open(pdf_name, "wb") as pdf_file:
            pdf_file.write(file_content)
        return pdf_name
