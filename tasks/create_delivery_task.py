from operator import attrgetter
from typing import List

from documents_generator.DeliveryGenerator import DeliveryGenerator
from documents_generator.RecordGenerator import RecordGenerator
from helpers.common import generate_documents
from models.record import RecordModel, RecordState
from models.product import ProductBoxModel
from app import create_app


def create_delivery(**request):
    app = create_app()
    with app.app_context():
        records = RecordModel.get_records(request["records"])
        records.sort(key=attrgetter('contract_id', 'date'))
        boxes = [ProductBoxModel.find_by_id(_id) for _id in request.get("boxes", [])]
        delivery_date = request["date"]
        uploaded_documents = []
        for record in records:
            record.change_state(RecordState.GENERATED, date=delivery_date)
            uploaded_documents.extend(generate_documents(gen=RecordGenerator, record=record))
        uploaded_documents.extend(generate_documents(gen=DeliveryGenerator,
                                                     records=records,
                                                     date=delivery_date,
                                                     driver=request["driver"],
                                                     boxes=boxes,
                                                     comments=request.get("comments", "")))
        return uploaded_documents


def get_create_delivery_progress(task_status, record_ids: List[int] = None, delivery_gen_offset_time=5):
    """
    Calculates progress based on RecordState change from PLANNED to GENERATED and task_status
    :param
    task_status: started, finished, failed
    records: list of records
    :return: 100 or RecordState.GENERATED/(RecordState.GENERATED+RecordState.PLANNED)
    """
    if task_status == "finished":
        return 100
    elif task_status == "failed":
        return -1
    records = [record.state for record in RecordModel.get_records(record_ids)]
    generated = records.count(RecordState.GENERATED)
    return round(generated / (generated + records.count(RecordState.PLANNED)), 2) * 100 - delivery_gen_offset_time
