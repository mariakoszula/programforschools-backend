from documents_generator.InvoiceDisposalGenerator import InvoiceDisposalGenerator
from tests.common import GoogleDriveFakeCommands, validate_document_creation


def test_invoice_generation(invoice_data):
    _, _, _, disposals = invoice_data
    invoice_disp_gen = InvoiceDisposalGenerator(disposals, _output_dir="gen", _drive_tool=GoogleDriveFakeCommands)
    validate_document_creation(invoice_disp_gen, InvoiceDisposalGenerator, "Podsumowanie_faktur_dla_Wn_1.docx")
    assert invoice_disp_gen.data["app_title"] == "I 2023/2024, Wniosek 1/1/2023/2024"
    assert invoice_disp_gen.data["milk_sum"] == "510"
    assert invoice_disp_gen.data["apple_sum"] == "22.30"
    assert invoice_disp_gen.data["kohlrabi_sum"] == "20.50"
