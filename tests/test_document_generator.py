from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.config_parser import config_parser
import pytest
from os import path, remove
from tests.common import all_fields_to_marge_are_in_file
from shutil import rmtree
from helpers.file_folder_creator import DirectoryCreator
from tests.common_data import program as program_data
from helpers.google_drive import GoogleDriveCommands, DOCX_MIME_TYPE, PDF_MIME_TYPE


class CustomDocumentGenerator(DocumentGenerator):
    template_document = path.join(config_parser.get('DocTemplates', 'directory'),
                                  config_parser.get('DocTemplates', 'test'))
    directory_name = path.join(
        DirectoryCreator.get_main_dir(school_year=program_data["school_year"], semester_no=program_data["semester_no"]),
        "TEST")

    def prepare_data(self):
        self._document.merge(**self.fields_to_merge)

    def __init__(self, **fields_to_merge):
        self.fields_to_merge = fields_to_merge
        DocumentGenerator.__init__(self,
                                   template_document=CustomDocumentGenerator.template_document,
                                   output_directory=CustomDocumentGenerator.directory_name,
                                   output_name="test_file.docx")


@pytest.fixture
def document_generator(request):
    test_doc_gen = CustomDocumentGenerator(**request.param)
    yield test_doc_gen
    print(f"dir to remove: {test_doc_gen.directory_name}")
    rmtree(test_doc_gen.directory_name)


valid_fields = {'dummy_data_no': 125, 'dummy_data': "Testing document generation"}


@pytest.mark.parametrize('document_generator', [valid_fields], indirect=["document_generator"])
def test_successful_generation(document_generator):
    document_generator.generate()
    assert isinstance(document_generator, CustomDocumentGenerator)
    assert len(document_generator.generated_documents) == 1
    assert path.isdir(document_generator.directory_name)
    all_fields_to_marge_are_in_file(document_generator.generated_documents[0].name,
                                    **document_generator.fields_to_merge)


@pytest.mark.parametrize('document_generator', [{'dummy_data_no': 125},
                                                {'dummy_data_no': 1, 'dummy_data': 2, 'dummy_extra_field': 12}],
                         indirect=["document_generator"])
def test_missing_or_extra_merge_field_raises_exception(document_generator):
    with pytest.raises(ValueError):
        document_generator.generate()
        assert len(document_generator.generated_documents) == 0


@pytest.mark.parametrize('document_generator', [valid_fields], indirect=["document_generator"])
def test_successful_remote_upload(initial_program_setup, document_generator):
    document_generator.generate()
    document_generator.upload_files_to_remote_drive()
    assert len([gen.web_view_link for gen in document_generator.generated_documents if gen.web_view_link]) == 1


@pytest.fixture
def uploaded_file():
    (file_id, _) = GoogleDriveCommands.upload_file(CustomDocumentGenerator.template_document, mime_type=DOCX_MIME_TYPE)
    yield file_id
    GoogleDriveCommands.remove(file_id)
    file_to_remove = CustomDocumentGenerator.template_document.replace(DocumentGenerator.DOCX_EXT,
                                                                       DocumentGenerator.PDF_EXT)
    try:
        remove(file_to_remove)
    except FileNotFoundError:
        print(f"{file_to_remove} does not exists")


def test_successful_pdf_generation(uploaded_file):
    pdf_name = DocumentGenerator.export_to_pdf(file_name=CustomDocumentGenerator.template_document,
                                               source_file_id=uploaded_file)
    with open(pdf_name, "rb") as pdf_file:
        content = pdf_file.read()
        assert b"PDF" in content
    assert "test_file.pdf" in pdf_name
