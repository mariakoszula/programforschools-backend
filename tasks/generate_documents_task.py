import asyncio
from helpers.logger import app_logger
from typing import List
from documents_generator.DocumentGenerator import DocumentGenerator, DirectoryCreatorError
from helpers.google_drive import GoogleDriveCommandsAsync, FileData
from threading import Thread


def __get_results(files_data: List[FileData]):
    generator: DocumentGenerator
    return [str(file_data) for file_data in files_data]


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


async def generate_documents_async(generators_init_data: List[tuple]):
    produced_generators = get_generator_list(generators_init_data)
    run_generate_documents(produced_generators)

    generator: DocumentGenerator
    uploaded_documents = []
    docx_files_to_upload = [generator.generated_document for generator in produced_generators if
                            generator.generated_document]
    uploaded_documents.extend(await GoogleDriveCommandsAsync.upload_many(docx_files_to_upload))

    pdf_files_to_upload = await GoogleDriveCommandsAsync.convert_to_pdf_many(uploaded_documents)
    uploaded_documents.extend(await GoogleDriveCommandsAsync.upload_many(pdf_files_to_upload))

    return __get_results(uploaded_documents)
