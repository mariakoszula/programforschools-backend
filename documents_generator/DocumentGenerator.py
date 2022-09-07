from helpers.logger import app_logger
from mailmerge import MailMerge
from abc import ABC, abstractmethod
from shutil import copy
from os import path, makedirs, remove, rename
from typing import List
import subprocess
from helpers.google_drive import GoogleDriveCommands, DOCX_MIME_TYPE, PDF_MIME_TYPE


class DocumentGenerator(ABC):
    PDF_GENERATION_TRIES = 5

    def __init__(self, template_document, output_directory, output_name):
        if not path.exists(template_document):
            app_logger.error("[%s] template document: %s does not exists", __class__.__name__, template_document)
        self.generated_documents: List[str] = []
        self.output_directory = output_directory
        self.output_doc_name = output_name

        self.template_document = template_document
        self._document = self.__start_doc_gen()
        self.__fields_to_merge = self._document.get_merge_fields()

        super(DocumentGenerator, self).__init__()

    def generate(self, gen_pdf=True) -> None:
        self.prepare_data()
        file = path.join(self.output_directory, self.output_doc_name)
        try:
            self.__end_doc_gen(file)
            if gen_pdf:
                output = DocumentGenerator.generate_pdf(file, self.output_directory)
                self.generated_documents.append(output)
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
    def generate_pdf(docx_to_convert, output_dir) -> str:
        try:
            docx_to_convert = path.normpath(docx_to_convert)

            file_parts = path.split(docx_to_convert)
            output_file = path.join(file_parts[0], file_parts[1].replace('.docx', '.pdf'))
            args = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_dir,
                    docx_to_convert]
            results = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3000,
                                     check=True)
            if not path.exists(output_file):
                raise ValueError(f"Pdf not generated: {output_file} {results.stderr}")
            app_logger.info(f"Success: Document {docx_to_convert} saved in {output_file}")
            return output_file
        except Exception as e:
            app_logger.error("[%s] Serious error when generating pdf from docx %s out_dir %s: err_msg: %s.",
                             __class__.__name__, docx_to_convert, output_file, e)

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
        self.generated_documents.append(generated_file)
        app_logger.debug("[%s] Created new output file: %s", __class__.__name__, generated_file, )

    @abstractmethod
    def prepare_data(self):
        pass

    def upload_files_to_remote_drive(self):
        # TODO check if file uploaded if not retry
        # Check if file exists if not upload
        # use specified folder id stored in database
        for file in self.generated_documents:
            file_id = None
            if 'pdf' in file:
                file_id = GoogleDriveCommands.upload_file(path_to_file=file,
                                                          mime_type=PDF_MIME_TYPE)
            elif "docx" in file:
                file_id = GoogleDriveCommands.upload_file(path_to_file=file,
                                                          mime_type=DOCX_MIME_TYPE)
            if file_id:
                app_logger.info(f"File '{file}' successfully uploaded with id {file_id}")

