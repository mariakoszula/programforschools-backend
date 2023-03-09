import pytest
from models.directory_tree import DirectoryTreeModel
from models.program import ProgramModel
from tests.common_data import get_program_data
from tests.common_data import company as company_data
from models.company import CompanyModel
from helpers.common import get_parent_and_children_directories
from os import path

DUMMY_GOOGLE_ID = "asdfas343"
SECOND_DUMMY_GOOGLE_ID = "55sdf3r3qsdf"
THIRD_DUMMY_GOOGLE_ID = "55sddddf3r3qsdf"


@pytest.fixture
def setup_base_data(db_session):
    company = CompanyModel(**company_data)
    company.save_to_db()
    program = ProgramModel(**get_program_data(company.id))
    program.save_to_db()
    main_directory_tree = DirectoryTreeModel(
        name="main_dir",
        google_id=DUMMY_GOOGLE_ID,
        parent_id=None,
        program_id=program.id
    )
    main_directory_tree.save_to_db()
    second_directory = DirectoryTreeModel(
        name="second_dir",
        google_id=SECOND_DUMMY_GOOGLE_ID,
        parent_id=main_directory_tree.id,
        program_id=program.id
    )
    second_directory.save_to_db()
    third_directory = DirectoryTreeModel(
        name="third_dir",
        google_id=THIRD_DUMMY_GOOGLE_ID,
        parent_id=second_directory.id,
        program_id=program.id
    )
    third_directory.save_to_db()
    yield main_directory_tree, second_directory, third_directory
    third_directory.delete_from_db()
    second_directory.delete_from_db()
    main_directory_tree.delete_from_db()
    program.delete_from_db()
    company.delete_from_db()


def test_get_children_and_parent(setup_base_data):
    main_directory_tree, second_directory, third_directory = setup_base_data
    path_to_file = path.join(main_directory_tree.name, second_directory.name, third_directory.name)
    (parent, children) = DirectoryTreeModel.get_children_and_parent(path_to_file, contains_file_name=True)
    assert parent is main_directory_tree
    assert children == ["second_dir"]
    (parent, children) = DirectoryTreeModel.get_children_and_parent(path_to_file, contains_file_name=False)
    assert parent is main_directory_tree
    assert children == ["second_dir", "third_dir"]


@pytest.mark.parametrize('path_to_file, skip_last, expected_parent, expected_children', [
    ("/main_dir/second_directory", True, "main_dir", []),
    ("main_dir/second_directory", False, "main_dir", ["second_directory"]),
    ("\\test", False, "test", []),
    ("main\\second\\third\\file.docx", False, "main", ["second", "third", "file.docx"]),
    ("main/second/third/file.docx", True, "main", ["second", "third"])
])
def test_parent_and_children_split_success(path_to_file, skip_last, expected_parent, expected_children):
    (parent, children) = get_parent_and_children_directories(path_to_file, skip_last=skip_last)
    assert parent == expected_parent
    assert children == expected_children
