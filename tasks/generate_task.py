from operator import attrgetter
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


