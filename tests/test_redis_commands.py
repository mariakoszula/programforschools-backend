import pytest

from helpers.common import FileData
from helpers.redis_commands import save_uploaded_files, remove_file, get_uploaded_file
from pytest_redis import factories

redis_external = factories.redisdb('redis_nooproc')


def test_successful_save_and_removed(redis_external):
    test_file_1 = FileData(_name="test_file_name_1", _webViewLink="http://dummy.com/asdf",
                           _id="123873147fhdsb39833uhdsadfwe")
    uploaded_files = save_uploaded_files([test_file_1], redis_connection=redis_external)
    assert uploaded_files == 1
    test_file_res_1 = get_uploaded_file(test_file_1.name, redis_external)
    assert test_file_res_1.name == test_file_1.name
    assert test_file_res_1.id == test_file_1.id
    assert test_file_res_1.web_view_link == test_file_1.web_view_link
    assert 1 == remove_file(test_file_1, redis_connection=redis_external)
    with pytest.raises(ValueError):
        get_uploaded_file(test_file_1.name, redis_connection=redis_external)



