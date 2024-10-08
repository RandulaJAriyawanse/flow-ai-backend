from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .utils import get_env
from .models import ChatHistory, UserChats
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from typing import TypedDict, Annotated
from asgiref.sync import sync_to_async
from langgraph.prebuilt import ToolNode, tools_condition
from datetime import datetime
import json
import time
import environ
import os
from chatbot_app.llm_tools.api_tools.api_call import get_data

OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL")
TEMPERATURE = get_env("TEMPERATURE")
# MAX_TOKEN = get_env("MAX_TOKEN")

os.environ["LANGCHAIN_TRACING_V2"] = get_env("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_ENDPOINT"] = get_env("LANGCHAIN_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = get_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = get_env("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = get_env("LANGCHAIN_CALLBACKS_BACKGROUND")


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


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


def create_graph(state):
    llm = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=TEMPERATURE,
        # max_tokens=MAX_TOKEN,
        # streaming=True,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant that has access to tools to answer the user's question"
                "\n\nFor reference the time now is {time}",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now())

    tools = [get_data]
    chain = prompt | llm.bind_tools(tools, tool_choice="get_data")

    def first_assistant(state: State):
        return {"messages": [chain.invoke(state)]}

    def final_assistant(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    builder = StateGraph(state)
    builder.add_node("assistant", first_assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("final_assistant", final_assistant)
    builder.set_entry_point("assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "final_assistant")
    graph = builder.compile()
    return graph


async def get_answer(question: str, user_id, pdf_store_id=None):
    st = time.time()
    history_data = await get_message_history(user_id)
    history_data.append(("user", question))

    chain = create_graph(State)
    tool_content = None

    config = {
        "configurable": {
            "question": question,
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
