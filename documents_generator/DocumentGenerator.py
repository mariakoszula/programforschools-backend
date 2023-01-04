from helpers.file_folder_creator import DirectoryCreator
from helpers.logger import app_logger
from mailmerge import MailMerge
from abc import ABC, abstractmethod
from shutil import copy
from os import path, makedirs, remove, rename
from typing import List
from helpers.google_drive import GoogleDriveCommands, DOCX_MIME_TYPE, PDF_MIME_TYPE, FileData
from models.directory_tree import DirectoryTreeModel


class DirectoryCreatorError(Exception):
    pass


class DocumentGenerator(ABC):
    DOCX_EXT = ".docx"
    PDF_EXT = ".pdf"

    def __init__(self, *, template_document, output_directory, output_name, drive_tool=GoogleDriveCommands):
        self.drive_tool = drive_tool
        if not path.exists(template_document):
            app_logger.error("[%s] template document: %s does not exists", __class__.__name__, template_document)
        self.generated_documents: List[FileData] = []
        self.output_directory = output_directory
        self.output_doc_name = output_name
        self.template_document = template_document

        self.file_path = path.join(self.output_directory, self.output_doc_name)
        self.remote_parent_id = self.__prepare_remote_parent()
        self._document = self.__start_doc_gen()
        self.__document_merge = self._document.merge
        self._document.merge = self.__run_field_validation_and_merge
        self.__fields_to_merge = self._document.get_merge_fields()

        super(DocumentGenerator, self).__init__()

    def __prepare_remote_parent(self):
        try:
            DirectoryCreator.create_remote_tree(self.output_directory)
            return DirectoryTreeModel.get_google_parent_directory(self.file_path)
        except Exception as e:
            app_logger.error(f"During creation of directory tree{e}")
            raise DirectoryCreatorError()

    def __check_for_missing_or_extra_keys(self, given_keys):
        missing_fields = [key for key in self.__fields_to_merge if key not in given_keys]
        if len(missing_fields):
            raise ValueError(f"Missing fields from template {missing_fields}")
        extra_fields = [key for key in given_keys if key not in self.__fields_to_merge]
        if len(extra_fields):
            raise ValueError(f"Extra fields not in template {extra_fields}")

    def __run_field_validation_and_merge(self, parts=None, **fields):
        if not parts:
            try:
                self.__check_for_missing_or_extra_keys(fields.keys())
            except ValueError as e:
                app_logger.warn(f"{e}")
            for key, value in fields.items():
                fields[key] = str(value)
        self.__document_merge(**fields)

    def generate(self):
        self.prepare_data()
        try:
            self.__end_doc_gen(self.file_path)
            return self
        except ValueError as e:
            app_logger.error(f"Problem occurred during generating document {self.file_path}. [{e}]")

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
        for index, file_data in enumerate(self.generated_documents):
            if file_type not in file_data.name:
                continue
            uploaded_file_id, web_link = self.drive_tool.upload_file(path_to_file=file_data.name,
                                                                     mime_type=file_data.mime_type,
                                                                     parent_id=self.remote_parent_id.google_id)
            if uploaded_file_id:
                self.generated_documents[index].id = uploaded_file_id
                self.generated_documents[index].web_view_link = web_link
                app_logger.info(
                    f"File '{file_data.name}' successfully uploaded with id {uploaded_file_id} to "
                    f"{self.remote_parent_id}")

            else:
                app_logger.error(f"Failed to upload file '{file_data.name}' to {self.remote_parent_id}")
        return self

    def upload_pdf_files_to_remote_drive(self):
        return self.upload_files_to_remote_drive(file_type=DocumentGenerator.PDF_EXT)

    def export_files_to_pdf(self):
        files = list(filter(lambda file: DocumentGenerator.DOCX_EXT in file.name, self.generated_documents))
        file_data: FileData
        for file_data in files:
            self.generated_documents.append(
                FileData(_name=DocumentGenerator.export_to_pdf(file_data.name, file_data.id, self.drive_tool),
                         _mime_type=PDF_MIME_TYPE))
        return self

    @staticmethod
    def export_to_pdf(file_name, source_file_id, drive_tool=GoogleDriveCommands):
        file_content = drive_tool.convert_to_pdf(source_file_id)
        pdf_name = file_name.replace(DocumentGenerator.DOCX_EXT, DocumentGenerator.PDF_EXT)
        with open(pdf_name, "wb") as pdf_file:
            pdf_file.write(file_content)
        return pdf_name
