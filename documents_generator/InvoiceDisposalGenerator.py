from os import path

from documents_generator.DocumentGenerator import DocumentGenerator
from helpers.config_parser import config_parser
from helpers.date_converter import DateConverter
from helpers.google_drive import GoogleDriveCommands
from models.application import ApplicationModel
from models.invoice import InvoiceDisposalModel, InvoiceModel, InvoiceProductModel
from typing import List, Set, Dict

from models.product import ProductModel
from models.program import ProgramModel

EMPTY = "-"


def get_app_name_for_dir(applications: Set[ApplicationModel]):
    return "_".join([f"{a.no}" for a in applications])


def get_app_title(applications: Set[ApplicationModel], program):
    output = f"{program.get_current_semester()} {program.school_year}, "
    output += ",".join([f"Wniosek {a}" for a in applications])
    return output


def prepare_product_invoice_map(invoice_disposals: List[InvoiceDisposalModel]):
    output: Dict[ProductModel, List[InvoiceDisposalModel]] = dict()
    tmp = ProductModel.all()
    for product in tmp:
        output[product] = []
        for _id in invoice_disposals:
            if _id.invoice_product.product_store.product == product:
                output[product].append(_id)
    return output


def amount_format(product: ProductModel, amount):
    return f"{amount:.2f}" if product.weight.is_kg() else f"{amount:.0f}"


def get_additional_disp_info(product: ProductModel, amount, disp_amount):
    if amount == disp_amount:
        return EMPTY
    return f"W tym okresie wydano: {amount_format(product, disp_amount)}\nNa kolejny okres przechodzi: {amount_format(product, amount - disp_amount)}"


class InvoiceDisposalGenerator(DocumentGenerator):
    def prepare_data(self):
        for product, invoice_list in self.product_invoice_map.items():
            self.merge_rows(f"{product.template_name}_lp", self.__invoice_info(product, invoice_list))
        self.merge(**self.data)

    def __init__(self, invoice_disposals: List[InvoiceDisposalModel], _output_dir=None,
                 _drive_tool=GoogleDriveCommands):
        if not len(invoice_disposals):
            raise ValueError("List with invoice_disposals cannot be empty")
        self.product_invoice_map: Dict[ProductModel, List[InvoiceDisposalModel]] = prepare_product_invoice_map(
            invoice_disposals)
        applications = set()
        for id in invoice_disposals:
            applications.add(id.application)
        self.program: ProgramModel = next(iter(applications)).program
        if _output_dir is None:
            _output_dir = path.join(self.program.get_main_dir(), config_parser.get('Directories', 'invoice_disposal'))
        self.data = dict()
        self.data["app_title"] = get_app_title(applications, self.program)
        _output_name = config_parser.get('DocNames', 'invoice_disposal').format(get_app_name_for_dir(applications))
        DocumentGenerator.__init__(self,
                                   template_document=config_parser.get('DocTemplates', 'invoice_disposal'),
                                   output_directory=_output_dir,
                                   output_name=_output_name,
                                   drive_tool=_drive_tool)

    def __invoice_info(self, product: ProductModel, invoice_disposals: List[InvoiceDisposalModel]):
        output = []
        prefix = product.template_name
        if not invoice_disposals:
            output.append({
                f"{prefix}_lp": EMPTY,
                f"{prefix}_invoice_name": EMPTY,
                f"{prefix}_date": EMPTY,
                f"{prefix}_amount": EMPTY,
                f"{prefix}_additional_info": EMPTY,
            })
        id: InvoiceDisposalModel
        sum_ = 0
        for lp, id in enumerate(invoice_disposals, start=1):
            invoice_product: InvoiceProductModel = id.invoice_product
            invoice: InvoiceModel = id.invoice_product.invoice
            sum_ += invoice_product.amount
            output.append({
                f"{prefix}_lp": lp,
                f"{prefix}_date": DateConverter.convert_date_to_string(invoice.date),
                f"{prefix}_invoice_name": invoice.name,
                f"{prefix}_amount": amount_format(product, invoice_product.amount),
                f"{prefix}_additional_info": get_additional_disp_info(product, invoice_product.amount, id.amount),
            })
        self.data[f"{prefix}_sum"] = amount_format(product, sum_)
        return output
