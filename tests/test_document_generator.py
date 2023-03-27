from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.config_parser import config_parser
from os import path, remove
from tests.common import all_fields_to_marge_are_in_file
from shutil import rmtree
from typing import List
from helpers.google_drive import FileData, GoogleDriveCommands, GoogleDriveCommandsAsync
from helpers.common import DOC_GOOGLE_MIME_TYPE, DOCX_EXT, PDF_EXT, get_mime_type
from tasks.generate_documents_task import generate_documents
from models.directory_tree import DirectoryTreeModel
import pytest


class CustomDocumentGenerator(DocumentGenerator):
    template_document = path.join("helper_files",
                                  config_parser.get('DocTemplates', 'test').format(""))
    main_directory_name = "TEST_PROGRAM_2022_2023_SEMESTR_2"

    def prepare_data(self):
        self.merge(**self.fields_to_merge)

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
def test_successful_generation(initial_app_setup, document_generator):
    document_generator.generate()
    assert isinstance(document_generator, CustomDocumentGenerator)
    assert len(document_generator.generated_documents) == 1
    assert path.isdir(document_generator.test_directory_path)
    all_fields_to_marge_are_in_file(document_generator.generated_documents[0].name,
                                    **document_generator.fields_to_merge)


@pytest.mark.parametrize('document_generator', [valid_fields], indirect=["document_generator"])
def test_successful_remote_upload(initial_app_setup, document_generator):
    document_generator.generate()
    document_generator.upload_files_to_remote_drive()
    assert len([gen.web_view_link for gen in document_generator.generated_documents if gen.web_view_link]) == 1


@pytest.fixture
def uploaded_file():
    file_data = FileData(_name=CustomDocumentGenerator.template_document, _mime_type=DOC_GOOGLE_MIME_TYPE)
    (file_id, _) = GoogleDriveCommands.upload_file(file_data)
    yield file_id
    remove_created_pdf()
    GoogleDriveCommands.remove(file_id)


def remove_created_pdf():
    file_to_remove = CustomDocumentGenerator.template_document.replace(DOCX_EXT,
                                                                       PDF_EXT)
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


def prepare_generate_documents_data(loop_size):
    test_data = []
    for i in range(loop_size):
        args = valid_fields.copy()
        args["directory_name"] = f"TEST_{i}"
        test_data.append((CustomDocumentGenerator, args))
    return test_data


def __validate_successful_generation_test(res, no_of_items):
    assert len(res) == 2 * no_of_items
    results_str = "".join(res)
    assert (results_str.count("test_file.docx") == no_of_items)
    assert (results_str.count("https://drive.google.com") == no_of_items)
    assert (results_str.count("test_file.pdf") == no_of_items)
    assert (results_str.count("https://docs.google.com/document") == no_of_items)


def test_successful_generate_documents(initial_app_setup, remove_created_resources):
    for item in prepare_generate_documents_data(loop_size=1):
        results = generate_documents(item[0], **item[1])
        __validate_successful_generation_test(results, 1)
        assert DirectoryTreeModel.find_one_by_name(item[1]["directory_name"])


from pytest_redis import factories

redis_external = factories.redisdb('redis_nooproc')


@pytest.mark.asyncio
async def test_successful_generate_documents_async(initial_app_setup, remove_created_resources, redis_external):
    from tasks.generate_documents_task import create_generator_and_run
    loop_size = 2
    test_documents = prepare_generate_documents_data(loop_size)
    first: List[FileData] = await create_generator_and_run(test_documents, redis_conn=redis_external)
    for item in test_documents:
        assert DirectoryTreeModel.find_one_by_name(item[1]["directory_name"])
    __validate_successful_generation_test([str(res) for res in first], no_of_items=loop_size)
    second: List[FileData] = await create_generator_and_run(test_documents, redis_conn=redis_external)
    for item in test_documents:
        assert DirectoryTreeModel.find_one_by_name(item[1]["directory_name"])
    __validate_successful_generation_test([str(res) for res in second], no_of_items=loop_size)
    assert len(await GoogleDriveCommandsAsync.search(first[0].parent_id,
                                                     mime_type_query=get_mime_type(DOC_GOOGLE_MIME_TYPE))) == 1
