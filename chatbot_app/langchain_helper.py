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
MAX_TOKEN = get_env("MAX_TOKEN")

# LANGCHAIN_TRACING_V2 = True
# LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
# # LANGCHAIN_API_KEY = "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"
# LANGCHAIN_API_KEY = "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"
# LANGCHAIN_PROJECT = "FlowAIService"
# env = environ.Env(
#     # set casting, default value
#     DEBUG=(bool, False)
# )
# LANGCHAIN_TRACING_V2 = get_env("LANGCHAIN_TRACING_V2")
# LANGCHAIN_ENDPOINT = get_env("LANGCHAIN_ENDPOINT")
# LANGCHAIN_API_KEY = get_env("LANGCHAIN_API_KEY")
# LANGCHAIN_PROJECT = get_env("LANGCHAIN_PROJECT"

os.environ["LANGCHAIN_TRACING_V2"] = get_env("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_ENDPOINT"] = get_env("LANGCHAIN_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = get_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = get_env("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = get_env("LANGCHAIN_CALLBACKS_BACKGROUND")


async def get_message_history(user_id):
    print("LANGCHAIN_TRACING_V2: ", os.environ["LANGCHAIN_TRACING_V2"])
    print("LANGCHAIN_ENDPOINT: ", os.environ["LANGCHAIN_ENDPOINT"])
    print("LANGCHAIN_API_KEY: ", os.environ["LANGCHAIN_API_KEY"])
    print("LANGCHAIN_PROJECT: ", os.environ["LANGCHAIN_PROJECT"])
    print(
        "LANGCHAIN_CALLBACKS_BACKGROUND: ", os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"]
    )

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


def create_graph():
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

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant that has access to 2 tools that may be relevent in answering the user's question"
                "Use the tool get_AASB_information to answer any accounting related questions and use the tool get_invoices to get information about the user's invoices."
                "\nFor reference the date and time now is {time}",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now())

    model = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKEN,
        streaming=True,
    )

    tools = [get_AASB_information, get_invoices, get_single_invoice]
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


async def get_answer(question: str, user_id):
    st = time.time()
    history_data = await get_message_history(user_id)
    history_data.append(("user", question))
    chain = create_graph()
    tool_content = None
    response = chain.astream_events({"messages": history_data[-3:]}, version="v1")
    async for chunk in response:
        if chunk["event"] == "on_chat_model_stream":
            content = chunk["data"]["chunk"].content
            yield content
        elif chunk["event"] == "on_tool_end":
            if chunk["data"]["output"]:
                content = chunk["data"]["output"].content
                content_final = json.loads(content)
                tool_content = {"name": chunk["name"], "data": content_final["data"]}
    if tool_content:
        yield tool_content
    print("Full get answer time: ", time.time() - st)
