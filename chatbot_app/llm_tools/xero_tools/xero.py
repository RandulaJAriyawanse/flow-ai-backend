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
    company: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    invoice_contact: Optional[str] = None,
    overdue: Optional[bool] = None,
    sent_to_contact: Optional[bool] = None,
    invoice_status: Optional[List[InvoiceStatus]] = None,
) -> list[dict]:
    """Get invoices based on start time, end time, overdue or invoice status. Overdue will be explicity stated

    Args:
        company (str): The name of the company to search invoices for.
        start_date (Optional[date]): The start date of invoices to search for.
        end_date (Optional[date]): The end date of invoices to search for.
        invoice_contact (Optional[str]): The name of the contact the invoice was sent to.
        overdue (Optional[bool]): True if the user clearly requests for "overdue" invoices.
        sent_to_contact (Optional[bool]): True if invoice has been sent to the contact.
        invoice_status (Optional[List[InvoiceStatus]]): A list of invoice statuses to search for.

    Returns:
        list[dict]: A list of invoice dictionaries that match the search criteria.

    """
    print(
        "---------------------------starting_get_invoices---------------------------------"
    )
    print("company: ", company)
    print("start_date: ", start_date)
    print("end_date: ", end_date)
    print("contact_name: ", invoice_contact)
    print("overdue: ", overdue)
    print("invoice_status: ", invoice_status)
    try:
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
                "Type": item["Type"],
                "SentToContact": "sent" if item.get("SentToContact") else None,
            }
            simplified_results.append(simplified_item)

        # if company:
        #     query += f" for account {company}"

        simplified_results = [
            item for item in simplified_results if item["Type"] == "ACCREC"
        ]

        if start_date:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] >= start_date
            ]

        if end_date:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] <= end_date
            ]

        if invoice_contact:
            simplified_results = [
                item
                for item in simplified_results
                if item["Contact Name"] == invoice_contact
            ]

        if overdue:
            simplified_results = [
                item for item in simplified_results if item["Due Date"] < date.today()
            ]

        if sent_to_contact:
            simplified_results = [
                item for item in simplified_results if item["SentToContact"] == "sent"
            ]

        if invoice_status is None:
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
                return {
                    "error list": f"Invalid invoice status: {error_list}",
                    "data": "",
                }
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

        filter_string = ""
        if start_date:
            filter_string += f" from {start_date}"
        if end_date:
            filter_string += f" to {end_date}"
        if invoice_contact:
            filter_string += f" for {invoice_contact}"
        if overdue:
            filter_string += " that are overdue"
        if invoice_status:
            filter_string += f" with status {', '.join(invoice_status)}"

        instruction = f"Important Instruction - Only reply with the following: That there are {len(simplified_results)} invoices with a total amount due of {round(total_amount_due, 0)}{filter_string}."

        print("Instruction: ", instruction)
    except Exception as e:
        print("Error : ", e)
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
