from typing import List, Type, Tuple, Dict
from threading import Thread
from rq import get_current_job
from documents_generator.DocumentGenerator import DocumentGenerator, DirectoryCreatorError
from helpers.google_drive import GoogleDriveCommandsAsync
from helpers.logger import app_logger
from helpers.redis_commands import remove_old_save_new
from helpers.common import FileData
from helpers.redis_commands import conn as redis_connection
from rq import Queue, Connection
from app import create_app

NO_OF_GOOGLE_DRIVE_ACTIONS = 4  # 1. Docx gen, 2. upload, 3. pdf gen, 4. upload


def measure_time_callback(job, connection, result, *args, **kwargs):
    with create_app().app_context():
        app_logger.debug(f"Delivery job time diff: {job.ended_at - job.started_at}")


def queue_task(*, func, request, callback=measure_time_callback):
    with Connection(redis_connection):
        q = Queue()
        req_in = dict(**request.args)
        if request.is_json:
            req_in.update(**request.json)
        create_task = q.enqueue(func,
                                result_ttl=60 * 60,
                                on_success=callback,
                                **req_in)
    return {
               'task_id': create_task.get_id()
           }, 202


def setup_progress_meta(documents_no: int):
    job = get_current_job()
    if not job:
        return
    job.meta["documents_no"] = documents_no * NO_OF_GOOGLE_DRIVE_ACTIONS
    job.meta["finished_documents_no"] = 0
    job.save_meta()


def update_finished_documents_meta(documents_no: int):
    job = get_current_job()
    if not job:
        return
    job.meta["finished_documents_no"] += documents_no
    job.save_meta()


def calculate_progress(current_job):
    meta = current_job.get_meta(refresh=True)
    if meta.get("documents_no") and meta.get("finished_documents_no"):
        return meta.get("finished_documents_no") / meta.get("documents_no") * 100
    return 0


def get_generator(gen, **args):
    try:
        generator = gen(**args)
        return generator
    except DirectoryCreatorError:
        app_logger.error(f"Failed to create remote directory tree for {gen} with {args}")
    except TypeError as e:
        app_logger.error(f"{generator}: Problem occurred during document generation '{e}'")


def get_generator_list(generators_init_data: List[tuple]):
    generators = []
    for (gen, args) in generators_init_data:
        generator = get_generator(gen, **args)
        if generator:
            generators.append(generator)
    return generators


def start_thread(func, *args):
    _thread = Thread(target=func, args=args)
    _thread.start()
    return _thread


def stop_threads(threads):
    for thread in threads:
        thread.join()


def run_generate_documents(generators: List[DocumentGenerator]):
    threads = []
    for generator in generators:
        threads.append(start_thread(DocumentGenerator.generate, generator))
    stop_threads(threads)


async def upload_and_update_meta(func, input_doc):
    documents = await func(input_doc)
    update_finished_documents_meta(len(documents))
    return documents


async def generate_documents_async(generators_init_data: List[Tuple[Type[DocumentGenerator], Dict]], redis_conn=None) \
        -> List[FileData]:
    """
    Async function for generating documents based on template docx, upload them to GoogleDrive,
    generate pdf and upload pdf to GoogleDrive.
    :param generators_init_data: Use proper DocumentGenerator e.g. RecordGenerator and
                                 pass arguments as dict with arguments
    :param redis_conn: Extracted for testing purpose, by default will use url from config.ini: [Redis.url]
    :return: List[FileData] - List of all generated files with information about name, and google id
    """
    produced_generators = get_generator_list(generators_init_data)
    run_generate_documents(produced_generators)
    generator: DocumentGenerator
    uploaded_documents = []
    docx_files_to_upload = [generator.generated_document for generator in produced_generators if
                            generator.generated_document]
    update_finished_documents_meta(len(docx_files_to_upload))
    output = await upload_and_update_meta(GoogleDriveCommandsAsync.upload_many, docx_files_to_upload)
    uploaded_documents.extend(output)
    output = await upload_and_update_meta(GoogleDriveCommandsAsync.convert_to_pdf_many, output)
    output = await upload_and_update_meta(GoogleDriveCommandsAsync.upload_many, output)
    uploaded_documents.extend(output)
    remove_old_save_new(uploaded_documents, redis_conn)
    return uploaded_documents