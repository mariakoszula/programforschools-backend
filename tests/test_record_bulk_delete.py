import json
from models.record import RecordModel, RecordState
from models.product import ProductTypeModel

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

        record_4 = RecordModel("08.12.2023", contract.id, product_store_dairy)
        record_4.save_to_db()
        record_4.change_state(RecordState.DELIVERY_PLANNED)

        record_5 = RecordModel("13.12.2023", contract.id, product_store_dairy)
        record_5.save_to_db()
        record_5.change_state(RecordState.ASSIGN_NUMBER)

        record_6 = RecordModel("14.12.2023", contract.id, product_store_dairy)
        record_6.save_to_db()
        record_6.change_state(RecordState.DELIVERED)

        record_7 = RecordModel("12.12.2023", contract.id, product_store_dairy)
        record_7.save_to_db()
        record_7.change_state(RecordState.GENERATION_IN_PROGRESS, date="12.12.2023")

        response_failed = client_with_in_memory_db.delete("/records/bulk_delete",
                                                   data=json.dumps({"ids": [record_1.id, record_2.id, record_3.id]}),
                                                   content_type="application/json",
                                                   headers=auth_headers)
        assert response_failed.status_code == 400, f"Wrong response status code:{response_failed.status_code}"
        response_json = response_failed.get_json()
        print(response_json)

        response_success = client_with_in_memory_db.delete("/records/bulk_delete",
                                                   data=json.dumps({"ids": [record_1.id, record_2.id, record_3.id,
                                                                            record_4.id, record_5.id, record_6.id,
                                                                            record_7.id],
                                                                    "program_id": record_1.contract.program_id}),
                                                   content_type="application/json",
                                                   headers=auth_headers)
        assert response_success.status_code == 200, f"Wrong response status code:{response_success.status_code}"
        response_json = response_success.get_json()
        assert response_json['skipped'] == [2, 6, 7], f"Skipped records wrong value: {response_json['skipped']}"
        assert response_json['deleted'] == [1, 3, 4, 5], f"Delete records wrong value: {response_json['deleted']}"

        with client_with_in_memory_db.application.app_context():
            remaining_items = RecordModel.query.all()
            remaining_ids = [item.id for item in remaining_items]
            assert remaining_ids == [2, 6, 7], f"Failed when validateing bulk delete {remaining_ids}"