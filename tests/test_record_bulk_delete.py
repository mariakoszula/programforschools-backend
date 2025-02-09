import json
from models.record import RecordModel, RecordState


def test_bulk_delete(client_with_in_memory_db, auth_headers, setup_record_test_init, product_store_carrot):
    with client_with_in_memory_db.application.app_context():
        # Should NOT be deleted: GENERATED, DELIVERED, GENERATION_IN_PROGRESS
        # Should bet deleted: PLANNED, DELIVERY_PLANNED, ASSIGN_NUMBER
        contract, product_store_dairy, _ = setup_record_test_init
        record_1 = RecordModel("02.12.2023", contract.id, product_store_dairy)
        record_1.save_to_db()
        record_1.change_state(RecordState.PLANNED)
        record_2 = RecordModel("16.12.2023", contract.id, product_store_dairy)
        record_2.save_to_db()
        record_2.change_state(RecordState.GENERATED)

        # Should never be deleted because it is different type
        record_3 = RecordModel("02.12.2023", contract.id, product_store_carrot)
        record_3.save_to_db()
        record_3.change_state(RecordState.PLANNED)

        response = client_with_in_memory_db.delete("/records/bulk_delete",
                                                   data=json.dumps({"ids": [record_1.id, record_2.id, record_3.id]}),
                                                   content_type="application/json",
                                                   headers=auth_headers)
        assert response.status_code == 400, f"Wrong response status code:{response.status_code}"
        response_json = response.get_json()
        assert response_json == {"message": "dd"}, f"Wrong response: {response_json}"

        with client_with_in_memory_db.application.app_context():
            remaining_items = RecordModel.query.all()
            remaining_ids = [item.id for item in remaining_items]
            assert remaining_ids == [3]