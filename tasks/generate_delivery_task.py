from operator import attrgetter
from models.record import RecordModel, RecordState
from documents_generator.DeliveryGenerator import DeliveryGenerator, DeliveryRecordsGenerator
from documents_generator.RecordGenerator import RecordGenerator
from app import create_app
from models.product import ProductBoxModel
from tasks.generate_documents_task import queue_task, setup_progress_meta, generate_documents_async, \
    measure_time_callback


async def create_delivery_async(**request):
    with create_app().app_context():
        records = RecordModel.get_records(request["records"])
        records.sort(key=attrgetter('contract_id', 'date'))
        boxes = [ProductBoxModel.find_by_id(_id) for _id in request.get("boxes", [])]
        delivery_date = request["date"]
        for record in records:
            record.change_state(RecordState.GENERATION_IN_PROGRESS, date=delivery_date)
        delivery_args = {'records': records, 'date': delivery_date,
                         'driver': request["driver"],
                         'boxes': boxes,
                         'comments': request.get("comments", "")}
        input_docs = [(RecordGenerator, {'record': record}) for record in records]
        input_docs.append((DeliveryGenerator, delivery_args))
        input_docs.append((DeliveryRecordsGenerator, delivery_args))
        setup_progress_meta(len(input_docs))
        return await generate_documents_async(input_docs)


def on_success_delivery_update(job, connection, result, *args, **kwargs):
    with create_app().app_context():
        for record in RecordModel.get_records(job.kwargs['records']):
            record.change_state(RecordState.GENERATED)
        measure_time_callback(job, connection, result, *args, **kwargs)


def on_failure_delivery_update(job, connection, exception, *args, **kwargs):
    with create_app().app_context():
        for record in RecordModel.get_records(job.kwargs['records']):
            record.change_state(RecordState.PLANNED)


def queue_delivery(request):
    return queue_task(func=create_delivery_async,
                      callback=on_success_delivery_update,
                      request=request,
                      callback_failure=on_failure_delivery_update)

