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
import json
import time


OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL")
TEMPERATURE = get_env("TEMPERATURE")
MAX_TOKEN = get_env("MAX_TOKEN")


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
                "You are a helpful assistant that has access to a tool that will provide information about AASB Australian Accounting Standards. The response from the tool may only be partially relevent for the user's question",
            ),
            ("placeholder", "{messages}"),
        ]
    )
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
    print("Get message time: ", time.time() - st)
    history_data.append(("user", question))
    chain = create_graph()
    print("Create graph: ", time.time() - st)
    tool_content = None
    response = chain.astream_events({"messages": history_data[-3:]}, version="v1")
    print("Starting ")
    async for chunk in response:
        print("---------------------------------------------------------")
        print(chunk)
        if chunk["event"] == "on_chat_model_stream":
            content = chunk["data"]["chunk"].content
            yield content
        elif chunk["event"] == "on_tool_end":
            print("Tool end time: ", chunk)
            if chunk["data"]["output"]:
                content = chunk["data"]["output"].content
                content_final = json.loads(content)
                tool_content = {"name": chunk["name"], "data": content_final["data"]}
    if tool_content:
        yield tool_content
    print("Full get answer time: ", time.time() - st)
