from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.config_parser import config_parser
from os import path, remove
from tests.common import all_fields_to_marge_are_in_file
from shutil import rmtree
from helpers.file_folder_creator import DirectoryCreator
from tests.common_data import program as program_data
from helpers.google_drive import FileData, GoogleDriveCommands, DOCX_MIME_TYPE, GoogleDriveCommandsAsync, DriveCommands
from helpers.common import generate_documents
from models.directory_tree import DirectoryTreeModel
import pytest


class CustomDocumentGenerator(DocumentGenerator):
    template_document = path.join(config_parser.get('DocTemplates', 'directory'),
                                  config_parser.get('DocTemplates', 'test'))
    main_directory_name = DirectoryCreator.get_main_dir(school_year=program_data["school_year"],
                                                        semester_no=program_data["semester_no"])

    def prepare_data(self):
        self._document.merge(**self.fields_to_merge)

    def __init__(self, drive_tool=GoogleDriveCommands, directory_name="TEST", **fields_to_merge):
        self.test_directory_path = path.join(CustomDocumentGenerator.main_directory_name, directory_name)
        self.fields_to_merge = fields_to_merge
        DocumentGenerator.__init__(self,
                                   template_document=CustomDocumentGenerator.template_document,
                                   output_directory=self.test_directory_path,
                                   output_name="test_file.docx",
                                   drive_tool=drive_tool)


@pytest.fixture
def document_generator(request):
    test_doc_gen = CustomDocumentGenerator(drive_tool=GoogleDriveCommands, **request.param)
    yield test_doc_gen
    remove_local_directory()


def remove_local_directory():
    rmtree(CustomDocumentGenerator.main_directory_name)


valid_fields = {'dummy_data_no': 125, 'dummy_data': "Testing document generation"}


@pytest.mark.parametrize('document_generator', [valid_fields], indirect=["document_generator"])
def test_successful_generation(initial_program_setup, document_generator):
    document_generator.generate()
    assert isinstance(document_generator, CustomDocumentGenerator)
    assert len(document_generator.generated_documents) == 1
    assert path.isdir(document_generator.test_directory_path)
    all_fields_to_marge_are_in_file(document_generator.generated_documents[0].name,
                                    **document_generator.fields_to_merge)


@pytest.mark.parametrize('document_generator', [{'dummy_data_no': 125},
                                                {'dummy_data_no': 1, 'dummy_data': 2, 'dummy_extra_field': 12}],
                         indirect=["document_generator"])
def test_missing_or_extra_merge_field_raises_exception(initial_program_setup, document_generator):
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
    file_data = FileData(_name=CustomDocumentGenerator.template_document, _mime_type=DOCX_MIME_TYPE)
    (file_id, _) = GoogleDriveCommands.upload_file(file_data)
    yield file_id
    remove_created_pdf()


def remove_created_pdf():
    file_to_remove = CustomDocumentGenerator.template_document.replace(DocumentGenerator.DOCX_EXT,
                                                                       DocumentGenerator.PDF_EXT)
    try:
        remove(file_to_remove)
    except FileNotFoundError:
        print(f"{file_to_remove} does not exists")


def test_successful_pdf_generation(uploaded_file):
    pdf_name = DocumentGenerator.export_to_pdf(file_name=CustomDocumentGenerator.template_document,
                                               source_file_id=uploaded_file,
                                               drive_tool=GoogleDriveCommands)
    with open(pdf_name, "rb") as pdf_file:
        content = pdf_file.read()
        assert b"PDF" in content
    assert "test_file.pdf" in pdf_name


@pytest.fixture
def remove_created_resources():
    yield
    remove_local_directory()


def prepare_generate_documents_data(loop_size, drive_tool):
    test_data = []
    for i in range(loop_size):
        args = valid_fields.copy()
        args["directory_name"] = f"TEST_{i}"
        args["drive_tool"] = drive_tool
        test_data.append((CustomDocumentGenerator,  args))
    return test_data


def __validate_successful_generation_test(res, no_of_items):
    assert len(res) == 2 * no_of_items
    results_str = "".join(res)
    assert (results_str.count("test_file.docx") == no_of_items)
    assert (results_str.count("https://drive.google.com") == no_of_items)
    assert (results_str.count("test_file.pdf") == no_of_items)
    assert (results_str.count("https://docs.google.com/document") == no_of_items)


def test_successful_generate_documents(initial_program_setup, remove_created_resources):
    for item in prepare_generate_documents_data(loop_size=1, drive_tool=GoogleDriveCommands):
        results = generate_documents(item[0], **item[1])
        __validate_successful_generation_test(results, 1)
        assert DirectoryTreeModel.find_one_by_name(item[1]["directory_name"])


@pytest.mark.asyncio
async def test_successful_generate_documents_async(initial_program_setup, remove_created_resources):
    from tasks.generate_documents_task import generate_documents_async
    loop_size = 50
    test_documents = prepare_generate_documents_data(loop_size, drive_tool=DriveCommands)
    results = await generate_documents_async(test_documents)
    for item in test_documents:
        assert DirectoryTreeModel.find_one_by_name(item[1]["directory_name"])
    __validate_successful_generation_test(results, no_of_items=loop_size)
    GoogleDriveCommandsAsync.clear_tmp()


