from operator import attrgetter
from models.record import RecordModel, RecordState, RecordNumbersChangedError
from documents_generator.DeliveryGenerator import DeliveryGenerator, DeliveryRecordsGenerator, SummaryGenerator
from app import create_app
from tasks.generate_documents_task import queue_task, setup_progress_meta, create_generator_and_run, \
    measure_time_callback
from helpers.db import db


async def create_delivery_async(**request):
    with create_app().app_context():
        records = RecordModel.get_records(request["records"])
        records.sort(key=attrgetter('contract_id', 'date'))
        delivery_date = request["date"]
        for record in records:
            record.change_state(RecordState.GENERATION_IN_PROGRESS, date=delivery_date)
        driver = request.get("driver", None)
        delivery_args = {'records': records, 'date': delivery_date,
                         'driver': driver,
                         'comments': request.get("comments", "")}
        input_docs = [(DeliveryGenerator, delivery_args)]
        discovered_changed_records = []
        if driver:
            for record in records:
                try:
                    record.change_state(RecordState.ASSIGN_NUMBER)
                except RecordNumbersChangedError as e:
                    discovered_changed_records.append(str(e))
            input_docs.append((DeliveryRecordsGenerator, delivery_args))
        if records:
            db.session.commit()
        setup_progress_meta(len(input_docs), notification=discovered_changed_records)
        return await create_generator_and_run(input_docs)


def on_success_delivery_update(job, connection, result, *args, **kwargs):
    with create_app().app_context():
        records = RecordModel.get_records(job.kwargs['records'])
        state: RecordState = RecordState.GENERATED
        if not job.kwargs.get('driver', None):
            state = RecordState.DELIVERY_PLANNED
        for record in records:
            record.change_state(state)
        if records:
            db.session.commit()
        measure_time_callback(job, connection, result, *args, **kwargs)


def on_failure_delivery_update(job, connection, exception, *args, **kwargs):
    with create_app().app_context():
        records = RecordModel.get_records(job.kwargs['records'])
        for record in records:
            record.change_state(RecordState.PLANNED)
        if records:
            db.session.commit()


def queue_delivery(request):
    return queue_task(func=create_delivery_async,
                      callback=on_success_delivery_update,
                      request=request,
                      callback_failure=on_failure_delivery_update)


async def create_week_summary_async(**request):
    with create_app().app_context():
        records = RecordModel.all_filtered_by_week(request["week_id"]).all()
        records.sort(key=attrgetter('contract_id', 'date'))
        input_docs = [(SummaryGenerator, {"records": records})]
        setup_progress_meta(len(input_docs))
        return await create_generator_and_run(input_docs)


def queue_week_summary(week_id):
    return queue_task(func=create_week_summary_async,
                      request={"week_id": week_id})
