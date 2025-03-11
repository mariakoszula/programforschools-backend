from helpers.common import FileData
from helpers.google_drive import DriveCommands
from models.contract import TimedAnnexModel, AnnexModel, ContractModel
from models.directory_tree import DirectoryTreeModel
from models.invoice import InvoiceProductModel, InvoiceModel, SupplierModel
from models.product import ProductStoreModel, ProductModel, ProductTypeModel, WeightTypeModel
from models.record import RecordState, RecordModel, RecordNumbersChangedError
from models.school import SchoolModel
from models.week import WeekModel
from os import path


def validate_document_creation(obj, gen, name_output):
    assert name_output in obj.remote_parent.name, f"{name_output} not found in {obj.remote_parent.name}"
    obj.generate()
    assert isinstance(obj, gen)
    assert len(obj.generated_documents) == 1
    assert path.isdir(obj.output_directory)
    assert name_output in obj.generated_documents[0].name, f"{name_output} not found in {obj.generated_documents[0].name}"



def all_fields_to_marge_are_in_file(file_name, **fields):
    import docx2txt
    text = docx2txt.process(file_name)
    for value in fields.values():
        assert str(value) in text and f"value: {value} not found in {text}"


def add_record(date, contract_id, product_store, final_state=RecordState.DELIVERED, db=None):
    try:
        record = RecordModel(date, contract_id, product_store)
        if db is not None:
            db.session.add(record)
            db.session.commit()
        record.save_to_db()
        record.change_state(RecordState.ASSIGN_NUMBER)
        record.change_state(RecordState.GENERATION_IN_PROGRESS, date=date)
        record.change_state(final_state)
    except RecordNumbersChangedError as e:
        print(e)
    return record


def clear_tables_schools():
    RecordModel.query.delete()
    TimedAnnexModel.query.delete()
    AnnexModel.query.delete()
    ContractModel.query.delete()
    SchoolModel.query.delete()


def clear_tables_common():
    clear_tables_schools()
    WeekModel.query.delete()
    InvoiceProductModel.query.delete()
    InvoiceModel.query.delete()
    SupplierModel.query.delete()
    ProductStoreModel.query.delete()
    ProductModel.query.delete()
    ProductTypeModel.query.delete()
    WeightTypeModel.query.delete()


class GoogleDriveFakeCommands(DriveCommands):
    @staticmethod
    def upload_file(file: FileData):
        pass

    @staticmethod
    def convert_to_pdf(source_file_id):
        pass

    @staticmethod
    def search(parent_id="", mime_type_query="", recursive_search=True):
        pass

    @staticmethod
    def create_directory(parent_directory_id, directory_name):
        pass

    @staticmethod
    def prepare_remote_parent(output_directory, file_path):
        return DirectoryTreeModel(file_path, "goolge_id", 1, "parent_id")
