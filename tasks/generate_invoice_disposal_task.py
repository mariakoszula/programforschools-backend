from documents_generator.InvoiceDisposalGenerator import InvoiceDisposalGenerator
from models.invoice import InvoiceDisposalModel
from tasks.generate_documents_task import queue_task, setup_progress_meta, create_generator_and_run
from helpers.db_context import async_with_db_context


@async_with_db_context
async def create_invoice_disposal_async(**request):
    invoice_disposals = InvoiceDisposalModel.all_filtered_by_application(request["applications"])
    input_docs = [(InvoiceDisposalGenerator, {'invoice_disposals': invoice_disposals})]
    setup_progress_meta(len(input_docs))
    return await create_generator_and_run(input_docs)


def queue_invoice_disposal(request):
    return queue_task(func=create_invoice_disposal_async,
                      request=request)