from app import create_app
from documents_generator.RecordRegisterGenerator import RecordRegisterGenerator
from documents_generator.RegisterGenerator import RegisterGenerator
from models.program import ProgramModel
from tasks.generate_documents_task import queue_task, setup_progress_meta, create_generator_and_run


async def create_register_async(**request):
    with create_app().app_context():
        program = ProgramModel.find_by_id(request.get('program_id'))
        input_docs = [(RegisterGenerator, {'program': program})]
        setup_progress_meta(len(input_docs))
        return await create_generator_and_run(input_docs)


def queue_register(program_id):
    return queue_task(func=create_register_async,
                      request={'program_id': program_id})


async def create_record_register_async(**request):
    with create_app().app_context():
        program = ProgramModel.find_by_id(request.get('program_id'))
        input_docs = [(RecordRegisterGenerator, {'program': program})]
        setup_progress_meta(len(input_docs))
        return await create_generator_and_run(input_docs)


def queue_record_register(program_id):
    return queue_task(func=create_record_register_async,
                      request={'program_id': program_id})
