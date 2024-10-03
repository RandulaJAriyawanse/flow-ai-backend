from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.runnables import Runnable, RunnableConfig
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from datetime import datetime
import json
import time
import os
from datetime import date, datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel
from typing import List
import json


class ItemOutput(BaseModel):
    items: List[str]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


@tool
def get_data(
    state: State,
    start_date: Optional[date],
    end_date: Optional[date],
    *,
    config: RunnableConfig,
):
    """
    Retrieve financial stock data to ask any questions related to stock information.

    Args:
      start_date (Optional[date]): Optional start date.
      end_date (Optional[date]): Optional end date.
    """
    print("_____________________________________________________________________")
    print("Start Date: ", start_date)
    print("End Date: ", end_date)
    # global json_schema_raw
    print("test")
    try:
        with open("chatbot_app/llm_tools/api_tools/CBA.json", "r") as file:
            raw_data = json.load(file)
    except Exception as e:
        print("Error: ", e)
    with open("chatbot_app/llm_tools/api_tools/api_schema.json", "r") as file:
        json_schema = json.load(file)

    configuration = config.get("configurable", {})
    question = configuration.get("question", None)
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=os.getenv("TEMPERATURE"),
        # max_tokens=MAX_TOKEN,
        # streaming=True,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an assistant that creates a filter string based on the following JSON schema:\n
            {json_schema}
            """
                "\nThe filter string should return the dataset that contains the requested data, not the requested data itself. If unsure, return more data than necessary"
                "\nThe filter string separates the different json layers with “::” like 'Financials::Income_Statement::yearly'"
                # "\nHere is an example - if the user asks 'show me intangible assets over the last few years' the response should be 'Financials::Income_Statement::yearly'"
                "\nEnsure you only reply with the single filter string",
            ),
            (
                "placeholder",
                "{question}",
            ),  # this is the where the message history goes and give the model context of the previous messages.
        ]
    ).partial(json_schema=json_schema)

    chain = prompt | llm
    filter_response = None
    try:
        # Run the chain and get the filter response

        data = raw_data.copy()

        filter_response = chain.invoke({"question": [("user", question)]})

        # Split the filter response to get the keys
        keys = filter_response.content.split("::")

        # Try accessing raw_data using the filter keys
        for key in keys:
            data = data[key]
    except Exception as e:
        data = raw_data.copy()

        error_message = f"Running the function with your previous output {filter_response.content} gave the following error: {str(e)}"

        updated_question = question + f" \n{error_message}"
        filter_response = chain.invoke({"question": [("user", updated_question)]})

        keys = filter_response.content.split("::")
        for key in keys:
            data = data[key]

    for key in keys:
        try:
            json_schema = json_schema["properties"]
        except KeyError:
            try:
                json_schema = json_schema["patternProperties"]

            except KeyError:
                print("no pattern")
        json_schema = json_schema[key]

    json_string = json.dumps(json_schema)

    item_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "\nYou are an assistant that identifies what financial metrics a user is asking for an returning a string based on the following json schema"
                "\n{json_schema}"
                "\If nothing in the user's question matches, return an empty string",
            ),
            (
                "placeholder",
                "{question}",
            ),
        ]
    ).partial(json_schema=json_string)

    items_chain = item_prompt | llm.with_structured_output(ItemOutput)
    items = items_chain.invoke(
        {"question": [("user", question)], "filter": filter_response}
    )

    if not isinstance(data, (dict, list)):
        return {"data": data}

    # data = raw_data.copy()
    if items.items:
        # Debugging
        # for date, info in data.items():
        #     print(f"Date: {date}, Type of info: {type(info)}")
        #     if isinstance(info, dict):
        #         print(f"Info keys: {list(info.keys())}")
        #     else:
        #         print(f"Info (not dict): {info}")

        if all(isinstance(info, dict) for info in data.values()):
            data = {
                date: {col: info.get(col) for col in items.items if col in info}
                for date, info in data.items()
            }
        else:
            data = {col: data.get(col) for col in items.items if col in data}

    if not isinstance(data, (dict, list)):
        return {"data": data}

    try:
        if start_date:
            data = {
                date: info
                for date, info in data.items()
                if start_date <= datetime.strptime(date, "%Y-%m-%d").date()
            }
        if end_date:
            data = {
                date: info
                for date, info in data.items()
                if datetime.strptime(date, "%Y-%m-%d").date() <= end_date
            }
    except Exception as e:
        print("ERROR: ", e)

    if data == {} or []:
        data = "API returned no data"

    try:
        data = list(data.items())[:30]
    except Exception as e:
        print("")

    return {"data": data}
