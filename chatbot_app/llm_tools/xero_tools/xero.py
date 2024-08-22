from typing import Optional
from langchain_core.tools import tool
from datetime import date, datetime, timezone
from .dummy_data import *
from typing import Optional, List, Dict
from enum import Enum


def convert_xero_date(xero_date_str: str) -> datetime.date:
    timestamp = int(xero_date_str.strip("/Date()")) / 1000
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.date()


class InvoiceStatus(Enum):
    PAID = "paid"
    DRAFT = "draft"
    SUBMITTED = "submitted"
    AUTHORISED = "authorised"
    VOIDED = "voided"
    DELETED = "deleted"


@tool
async def get_invoices(
    # company: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    overdue: Optional[bool] = None,
    # invoice_number: Optional[str] = None,
    invoice_status: Optional[List[InvoiceStatus]] = None,
) -> list[dict]:
    """Get invoices based on start time, end time, overdue or invoice status. Overdue and will be explicity stated"""

    try:
        print(
            "start_date: ",
            start_date,
            "end_date: ",
            end_date,
            "invoice_status: ",
            invoice_status,
        )

        simplified_results = []

        print("LENGTH: ", len(dummy_invoices[0]["Invoices"]))
        for item in dummy_invoices[0]["Invoices"]:
            simplified_item = {
                "Contact Name": item["Contact"]["Name"],
                "Email": "support@cityagency.com",
                "Due Date": convert_xero_date(item["DueDate"]),
                "Total": item["Total"],
                "Currency Code": item["CurrencyCode"],
                "Invoice Number": item["InvoiceNumber"],
                "Amount Due": item["AmountDue"],
                "Xero URL": "https://go.xero.com/",
                "Status": item["Status"],
            }
            simplified_results.append(simplified_item)

        # if company:
        #     query += f" for account {company}"

        if start_date:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] >= start_date
            ]

        if end_date:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] <= start_date
            ]

        if overdue:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] < date.today()
            ]

        if invoice_status is None:
            print("$$$$$$$$$$$$$$$Invoice none")
            simplified_results = [
                item
                for item in simplified_results
                if item["Status"] in ["SUBMITTED", "AUTHORISED", "DRAFT"]
            ]
        else:
            invoice_status = [status.value.upper() for status in invoice_status]
            error_list = []
            for item in invoice_status:
                if item.upper() not in [
                    "SUBMITTED",
                    "AUTHORISED",
                    "DRAFT",
                    "PAID",
                    "VOIDED",
                    "DELETED",
                ]:
                    error_list.append(item)
            if error_list:
                print("error_list: ", error_list)
                return {"error": f"Invalid invoice status: {error_list}", "data": ""}
            else:
                simplified_results = [
                    item
                    for item in simplified_results
                    if item["Status"] in invoice_status
                ]
        for item in simplified_results:
            if isinstance(item["Due Date"], date):
                item["Due Date"] = item["Due Date"].isoformat()

        total_amount_due = 0
        for item in simplified_results:
            total_amount_due += item["Amount Due"]

        instruction = f"Important instruction - Only reply with a summary that there are {len(simplified_results)} invoices with a total amount due of {round(total_amount_due, 0)}."
    except Exception as e:
        print("Error: ", e)
        return {"error": "An error occurred", "data": ""}

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
