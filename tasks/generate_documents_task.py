import asyncio
from queue import Queue
from threading import Thread
from helpers.logger import app_logger
from typing import List
from documents_generator.DocumentGenerator import DocumentGenerator, DirectoryCreatorError


class ClosableQueue(Queue):
    SENTINEL = object()

    def close(self):
        self.put(self.SENTINEL)

    def __iter__(self):
        while True:
            item = self.get()
            try:
                if item is self.SENTINEL:
                    return
                yield item
            finally:
                self.task_done()


class StoppableWorker(Thread):
    def __init__(self, func, in_queue, out_queue):
        super().__init__()
        self.func = func
        self.in_queue = in_queue
        self.out_queue = out_queue

    def run(self):
        for item in self.in_queue:
            result = self.func(item)
            self.out_queue.put(result)


generate_queue = ClosableQueue()
export_to_pdf_queue = ClosableQueue()
upload_queue = ClosableQueue()
upload_pdf_queue = ClosableQueue()
done_queue = ClosableQueue()


def start_threads(count, *args):
    _threads = [StoppableWorker(*args) for _ in range(count)]
    for t in _threads:
        t.start()
    return _threads


def stop_threads(closable_queue, threads):
    for _ in threads:
        closable_queue.close()
    closable_queue.join()
    for thread in threads:
        thread.join()


def __get_results_from_done_queue_and_clear():
    app_logger.debug(f"Generated and uploaded documents for {done_queue.qsize()} items")
    generated_documents = []
    item: DocumentGenerator
    for item in done_queue.queue:
        generated_documents.extend([str(document) for document in item.generated_documents])
    done_queue.queue.clear()
    return generated_documents


def __run_generate_and_upload_documents(generators: List[DocumentGenerator]):
    generate_threads = start_threads(4, DocumentGenerator.generate, generate_queue, upload_queue)
    upload_threads = start_threads(4, DocumentGenerator.upload_files_to_remote_drive, upload_queue, export_to_pdf_queue)
    export_to_pdf_threads = start_threads(4, DocumentGenerator.export_files_to_pdf, export_to_pdf_queue,
                                          upload_pdf_queue)
    upload_pdf_threads = start_threads(4, DocumentGenerator.upload_pdf_files_to_remote_drive, upload_pdf_queue,
                                       done_queue)

    for generator in generators:
        queue_generator(generator)

    stop_threads(generate_queue, generate_threads)
    stop_threads(upload_queue, upload_threads)
    stop_threads(export_to_pdf_queue, export_to_pdf_threads)
    stop_threads(upload_pdf_queue, upload_pdf_threads)


def generate_documents(generators_init_data: List[tuple]):
    generators = []
    for (gen, args) in generators_init_data:
        try:
            generator = gen(**args)
        except DirectoryCreatorError:
            app_logger.error(f"Failed to create remote directory tree for {gen} with {args}")
        else:
            generators.append(generator)
    __run_generate_and_upload_documents(generators)
    return __get_results_from_done_queue_and_clear()


def queue_generator(generator: DocumentGenerator):
    try:
        app_logger.debug(f"{generator}")
        generate_queue.put(generator)
    except TypeError as e:
        app_logger.error(f"{generator}: Problem occurred during document generation '{e}'")



