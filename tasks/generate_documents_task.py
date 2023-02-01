from typing import List
from operator import attrgetter
from threading import Thread
from rq import get_current_job
from documents_generator.DocumentGenerator import DocumentGenerator, DirectoryCreatorError
from helpers.google_drive import GoogleDriveCommandsAsync
from helpers.logger import app_logger
from helpers.redis_commands import remove_old_save_new
from helpers.common import FileData
from models.record import RecordModel, RecordState
from documents_generator.DeliveryGenerator import DeliveryGenerator
from documents_generator.RecordGenerator import RecordGenerator
from app import create_app
from models.product import ProductBoxModel


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


NO_OF_GOOGLE_DRIVE_ACTIONS = 4  # Docx generation and upload, generate PDF and upload pdf to Google Drive


async def upload_and_update_meta(func, input_doc):
    documents = await func(input_doc)
    update_finished_documents_meta(len(documents))
    return documents


async def generate_documents_async(generators_init_data: List[tuple], redis_conn=None) -> List[FileData]:
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


async def create_delivery_async(**request):
    with create_app().app_context():
        records = RecordModel.get_records(request["records"])
        records.sort(key=attrgetter('contract_id', 'date'))
        boxes = [ProductBoxModel.find_by_id(_id) for _id in request.get("boxes", [])]
        delivery_date = request["date"]
        for record in records:
            record.change_state(RecordState.GENERATION_IN_PROGRESS, date=delivery_date)
        setup_progress_meta(len(records) + 1)
        generated_documents = await generate_documents_async([(RecordGenerator,
                                                               {'record': record}) for record in records])
        delivery_args = {'records': records, 'date': delivery_date,
                         'driver': request["driver"],
                         'boxes': boxes,
                         'comments': request.get("comments", "")}
        generated_documents.extend(await generate_documents_async([(DeliveryGenerator, delivery_args)]))
        return generated_documents


def on_success_delivery_update(job, connection, result, *args, **kwargs):
    with create_app().app_context():
        for record in RecordModel.get_records(job.kwargs['records']):
            record.change_state(RecordState.GENERATED)
        app_logger.debug(f"Delivery job time diff: {job.ended_at - job.started_at}")
