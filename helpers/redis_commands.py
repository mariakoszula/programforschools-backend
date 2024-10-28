from typing import List
import json
import redis
from os import environ
from helpers.google_drive import FileData
from helpers.config_parser import config_parser
from helpers.google_drive import GoogleDriveCommands
from helpers.logger import app_logger
from urllib.parse import urlparse

UPLOADED_FILES_DICT = "uploadedFilesDict"


url = urlparse(environ.get('REDIS_URL', config_parser.get('Redis', 'url')))
conn = redis.Redis(host=url.hostname, port=url.port, password=url.password, ssl=(url.scheme == "rediss"), ssl_cert_reqs=None)


def save_uploaded_files(files: List[FileData], redis_connection=conn):
    results = 0
    for file in files:
        assert isinstance(file, FileData)
        value = json.dumps({"name": file.name, "web_view_link": file.web_view_link, "id": file.id})
        results = results + redis_connection.hset(UPLOADED_FILES_DICT, file.name, value)
        app_logger.debug(f"Saved to redis {file.name} with id {file.id}")
    return results


def get_uploaded_file(name, redis_connection=conn) -> FileData:
    found = redis_connection.hget(UPLOADED_FILES_DICT, name)
    if not found:
        raise ValueError(f"Name {name} was not found in {UPLOADED_FILES_DICT}")
    d = json.loads(found)
    app_logger.debug(f'Get from redis {d["name"]} with id {d["id"]}')
    return FileData(_name=d["name"], _webViewLink=d["web_view_link"], _id=d["id"])


def remove_file(file_data: FileData, redis_connection=conn):
    app_logger.debug(f'Remove from redis {file_data.name} with id {file_data.id}')
    return redis_connection.hdel(UPLOADED_FILES_DICT, file_data.name)


def remove_old_save_new(files: List[FileData], redis_connection=conn):
    if redis_connection is None:
        redis_connection = conn
    for file in files:
        try:
            prev_file = get_uploaded_file(file.name, redis_connection)
            GoogleDriveCommands.remove(prev_file.id)
            remove_file(prev_file, redis_connection)
        except ValueError:
            continue
    save_uploaded_files(files, redis_connection)
