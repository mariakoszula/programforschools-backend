from app import create_app
from documents_generator.ApplicationGenerator import application_factory
from tasks.generate_documents_task import queue_task, setup_progress_meta, generate_documents_async


async def create_application_async(**request):
    with create_app().app_context():
        application = request.get("application")
        try:
            app_gen = application_factory(application, request.get("date"), request.get("start_week"),
                                          request.get("is_last", False))
        except ValueError as e:
            return str(e)
        input_docs_for_schools = app_gen.records_summary + app_gen.statements
        setup_progress_meta(len(input_docs_for_schools) + 1)
        results = await generate_documents_async(input_docs_for_schools)
        results.extend(await generate_documents_async([app_gen]))


def queue_application(request):
    return queue_task(func=create_application_async, request=request)
