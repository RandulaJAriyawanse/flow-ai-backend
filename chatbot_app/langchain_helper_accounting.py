from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .utils import get_env
from .models import ChatHistory, UserChats
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.runnables import Runnable, RunnableConfig
from typing import TypedDict, Annotated
from asgiref.sync import sync_to_async
from chatbot_app.llm_tools.rag import get_AASB_information
from chatbot_app.llm_tools.user_rag import get_user_file_information
from chatbot_app.llm_tools.xero_tools.xero import get_invoices, get_single_invoice
from langgraph.prebuilt import ToolNode, tools_condition
from datetime import datetime
import json
import time
import environ
import os

OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL")
TEMPERATURE = get_env("TEMPERATURE")
# MAX_TOKEN = get_env("MAX_TOKEN")

os.environ["LANGCHAIN_TRACING_V2"] = get_env("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_ENDPOINT"] = get_env("LANGCHAIN_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = get_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = get_env("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = get_env("LANGCHAIN_CALLBACKS_BACKGROUND")


async def get_message_history(user_id):
    user_chats = await sync_to_async(
        lambda: list(UserChats.objects.filter(user_id=user_id)),
        thread_sensitive=True,
    )()
    chat_histories = await sync_to_async(
        lambda: list(ChatHistory.objects.filter(chat__in=user_chats).order_by("id")),
        thread_sensitive=True,
    )()
    history_data = []
    for chat_history in chat_histories:
        history_data.append(("user", chat_history.user_query))
        history_data.append(("assistant", chat_history.bot_response))
    return history_data


def create_graph(pdf_store_id):
    class State(TypedDict):
        messages: Annotated[list[AnyMessage], add_messages]

    class Assistant:
        def __init__(self, runnable: Runnable):
            self.runnable = runnable

        def __call__(self, state: State):
            while True:
                result = self.runnable.invoke(state)
                break
            return {"messages": result}

    file_upload_message = (
        "\nThe user has also uploaded a file that they may be querying about"
        if pdf_store_id
        else ""
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant that has access to a tool to answer any accounting related questions."
                # "\nIf the question has the term 'AASB' in it, make sure to rephrase the question to remove the term before passing the question as an argument to the tool."
                # "\nUse the get_invoices tool to get information about the user's invoices."
                # "\nNote, you currently only have access to invoices in Xero"
                # f"{file_upload_message}"
                "\nFor reference, the date and time now is {time}",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now())

    model = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=TEMPERATURE,
        # max_tokens=MAX_TOKEN,
        streaming=True,
    )

    tools = [get_AASB_information]  # , get_invoices, get_single_invoice]
    if pdf_store_id:
        tools.append(get_user_file_information)
    chain = prompt | model.bind_tools(tools)
    builder = StateGraph(State)
    builder.add_node("assistant", Assistant(chain))
    builder.add_node("tools", ToolNode(tools))
    builder.set_entry_point("assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    graph = builder.compile()
    return graph


async def get_answer(question: str, user_id, pdf_store_id=None):
    st = time.time()
    history_data = await get_message_history(user_id)
    history_data.append(("user", question))

    chain = create_graph(pdf_store_id)
    tool_content = None

    config = {
        "configurable": {
            "pdf_store_id": pdf_store_id,
        }
    }
    response = chain.astream_events(
        {"messages": history_data[-3:]}, config, version="v1"
    )
    async for chunk in response:
        if chunk["event"] == "on_chat_model_stream":
            content = chunk["data"]["chunk"].content
            yield {"type": "chat_response", "data": content}
        elif chunk["event"] == "on_tool_end":
            if chunk["data"]["output"]:
                content = chunk["data"]["output"].content
                content_final = json.loads(content)
                tool_content = {
                    "type": "tool_response",
                    "name": chunk["name"],
                    "data": content_final["data"],
                }
                # temporarily
                if tool_content["name"] == "get_AASB_information":
                    for doc in tool_content["data"]:
                        doc["page_content"] = ""
    if tool_content:
        yield tool_content
    print("Full get answer time: ", time.time() - st)
