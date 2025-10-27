from helpers.common import get_output_name
from documents_generator.DocumentGenerator import DocumentGenerator
from models.invoice import SupplierModel
from helpers.config_parser import config_parser
from os import path
from datetime import datetime

from models.program import ProgramModel


class SuppliersGenerator(DocumentGenerator):

    @staticmethod
    def __prepare_supplier_data(supplier: SupplierModel, no):
        supplier_dict = dict()
        supplier_dict["no"] = no
        supplier_dict["name"] = supplier.name
        supplier_dict["address"] = supplier.address
        supplier_dict["nip"] = supplier.nip
        supplier_dict["contact"] = supplier.contact
        return supplier_dict

    def prepare_data(self):
        suppliers_to_merge = []
        for no, supplier in enumerate(self.suppliers, start=1):
            suppliers_to_merge.append(SuppliersGenerator.__prepare_supplier_data(supplier, no))

        self.merge_rows('no', suppliers_to_merge)
        self.merge(
            date=self.date)

    def __init__(self, program: ProgramModel):
        self.date = datetime.today().strftime('%d-%m-%Y')
        self.suppliers = SupplierModel.all()
        doc_template = config_parser.get('DocTemplates', 'suppliers_registry')
        suppliers_dir = config_parser.get('Directories', 'suppliers_registry')
        DocumentGenerator.__init__(self,
                                   template_document=doc_template,
                                   output_directory=path.join(program.get_main_dir(), suppliers_dir),
                                   output_name=get_output_name('suppliers_registry', self.date))

