from documents_generator.ApplicationGenerator import application_factory
from models.application import ApplicationModel
from tasks.generate_documents_task import queue_task, setup_progress_meta, generate_documents_async
from helpers.db_context import async_with_db_context


@async_with_db_context
async def create_application_async(**request):
    try:
        application = ApplicationModel.find_by_id(request.get("application_id"))
        app_gen = application_factory(application, request.get("date"), request.get("start_week"),
                                      request.get("is_last", False))
    except ValueError as e:
        return str(e)
    input_docs = app_gen.records_summary + app_gen.statements + [app_gen]
    setup_progress_meta(len(input_docs))
    return await generate_documents_async(input_docs, pdf=False)


def queue_application(request):
    return queue_task(func=create_application_async, request=request)
