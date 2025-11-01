from operator import attrgetter

from sqlalchemy.orm import load_only

from models.product import ProductTypeModel
from models.record import RecordModel, RecordState, RecordNumbersChangedError
from documents_generator.DeliveryGenerator import DeliveryGenerator, DeliveryRecordsGenerator, SummaryGenerator
from tasks.generate_documents_task import queue_task, setup_progress_meta, create_generator_and_run, \
    measure_time_callback
from helpers.db import db
from helpers.logger import app_logger
from helpers.db_context import async_with_db_context, sync_with_db_context


@async_with_db_context
async def create_delivery_async(**request):
    records = RecordModel.get_records(request["records"])
    records.sort(key=attrgetter('contract_id', 'date'))
    delivery_date = request["date"]

    # Prefetch all ProductTypeIds
    product_type_ids = {record.product_type_id for record in records}
    product_types = (
        ProductTypeModel.query
            .filter(ProductTypeModel.id.in_(product_type_ids))
            .options(load_only('id', 'name'))
            .all()
    )

    product_type_map = {pt.id: pt for pt in product_types}

    for record in records:
        record.product_type = product_type_map.get(record.product_type_id)
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
    db.session.commit()
    app_logger.info(f"create_delivery_async to database records_no: {len(records)}")

    # 2. Keep session open during generation but expunge objects
    db.session.expunge_all()

    setup_progress_meta(len(input_docs), notification=discovered_changed_records)
    generated_files = await create_generator_and_run(input_docs)
    return generated_files


@sync_with_db_context
def on_success_delivery_update(job, connection, result, *args, **kwargs):
    records = RecordModel.get_records(job.kwargs['records'])
    state: RecordState = RecordState.GENERATED
    if not job.kwargs.get('driver', None):
        state = RecordState.DELIVERY_PLANNED
    for record in records:
        record.change_state(state)

    app_logger.info(f"Saving to database records_no: {len(records)}")
    db.session.commit()

    measure_time_callback(job, connection, result, *args, **kwargs)


@sync_with_db_context
def on_failure_delivery_update(job, connection, exception, *args, **kwargs):
    records = RecordModel.get_records(job.kwargs['records'])
    for record in records:
        record.change_state(RecordState.PLANNED)
    app_logger.info(f"On failure to database records_no: {len(records)}")
    db.session.commit()


def queue_delivery(request):
    return queue_task(func=create_delivery_async,
                      callback=on_success_delivery_update,
                      request=request,
                      callback_failure=on_failure_delivery_update)


@async_with_db_context
async def create_week_summary_async(**request):
    records = RecordModel.all_filtered_by_week(request["week_id"]).all()
    records.sort(key=attrgetter('contract_id', 'date'))
    input_docs = [(SummaryGenerator, {"records": records})]

    setup_progress_meta(len(input_docs))
    db.session.expunge_all()

    return await create_generator_and_run(input_docs)


def queue_week_summary(week_id):
    return queue_task(func=create_week_summary_async,
                      request={"week_id": week_id})
