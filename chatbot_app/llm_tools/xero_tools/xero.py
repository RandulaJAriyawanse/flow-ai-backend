from typing import Optional
from langchain_core.tools import tool
from datetime import date, datetime
from .dummy_data import *


@tool
async def get_invoices(
    company: Optional[str] = None,
    start_time: Optional[date | datetime] = None,
    end_time: Optional[date | datetime] = None,
    overdue: Optional[bool] = None,
    invoice_number: Optional[str] = None,
) -> list[dict]:
    """Get invoices based on company, start time, end time, invoice number and overdue status"""

    query = "List of transactions"

    if company:
        query += f" for account {company}"

    if start_time:
        query += f" starting at {start_time}"

    if end_time:
        query += f" ending at {end_time}"

    if invoice_number:
        query += f" with invoice number {invoice_number}"

    if overdue:
        query += f" that are overdue"

    print(f"get_invoices query: {query}")

    result = {"result": dummy_invoices}

    simplified_results = []
    for item in dummy_invoices[0]["Invoices"]:
        print("-----------------@-----------------")
        simplified_item = {
            "Contact Name": item["Contact"]["Name"],
            "Email": "support@cityagency.com",
            "Due Date": item["DueDate"],
            "Total": item["Total"],
            "Currency Code": item["CurrencyCode"],
            "Invoice Number": item["InvoiceNumber"],
            "Amount Due": item["AmountDue"],
            "Xero URL": item["OnlineInvoiceUrl"],
        }
        simplified_results.append(simplified_item)

    total_amount_due = 0
    for item in simplified_results:
        total_amount_due += item["Amount Due"]

    instruction = f"You have already provided the list of invoices to the user. Unless they have asked about a specific invoice, just notify them that there are {len(simplified_results)} invoices with a total amount due of {round(total_amount_due, 0)}."
    print("instruction: ", instruction)

    return {"Instruction": instruction, "data": simplified_results}


@tool
async def get_single_invoice(
    invoice_number: Optional[str] = None,
) -> list[dict]:
    """Get single invoice based on invoice number"""
    print("starting...................")
    print("invoice_number: ", invoice_number)
    filtered_invoices = [
        item
        for item in dummy_invoices[0]["Invoices"]
        if item["InvoiceNumber"] == invoice_number
    ]
    print("filtered_invoices: ", filtered_invoices)
    return {"data": filtered_invoices[0]}
