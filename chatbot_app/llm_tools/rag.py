from django.db import connection
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from typing import Optional
from chatbot_app.utils import get_env
import os
import time
from langchain_core.runnables import RunnableConfig
from langchain_qdrant import QdrantVectorStore
import re

db_engine = "postgresql+psycopg"
db_name = get_env("DATABASE_NAME")
db_user = get_env("DATABASE_USER")
db_password = get_env("DATABASE_PASSWORD")
db_host = get_env("DATABASE_HOST")
db_port = get_env("DATABASE_PORT")

connection_string = (
    f"{db_engine}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)


def get_existing_vectorstore(collection):
    vectorstore = PGVector(
        embeddings=OpenAIEmbeddings(
            model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
        ),
        collection_name=collection,
        connection=connection_string,
    )
    return vectorstore


def get_qdrant_vectorstore(collection):
    print("Getting Qdrant Vectorstore")
    try:
        qdrant = QdrantVectorStore.from_existing_collection(
            embedding=OpenAIEmbeddings(
                model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
            ),
            collection_name=collection,
            # url="https://14cd586c-aeba-4d67-a140-5ebd595d9a2c.europe-west3-0.gcp.cloud.qdrant.io",
            url="localhost:6333",
        )
    except Exception as e:
        print("Error Qdrant: ", e)
    print("Qdrant: ", qdrant)
    return qdrant


@tool
async def get_AASB_information(rephrased_question, *, config: RunnableConfig):
    """
    Consult the AASB (Australian accounting standards board) standards for any question regarding Australian accounting standards.

    Args:
        rephrased_question (str): A rephrased version of the user's question that removes the term "AASB" from it.

    """
    st = time.time()
    print("Question: ", rephrased_question)
    configuration = config.get("configurable", {})
    passenger_id = configuration.get("passenger_id", None)
    print("Passenger ID: ", passenger_id)
    collection = "AASB10"
    new_question = re.sub(r"AASB ?\d*", "", rephrased_question)
    print("New Question: ", new_question)

    # vectorstore = get_qdrant_vectorstore(collection)
    vectorstore = get_existing_vectorstore(collection)

    # filter={"file_name": {"$eq": "AASB2 Share-based Payment"}}
    try:
        documents = vectorstore.similarity_search_with_score(
            new_question,
            k=3,
        )

        for doc, score in documents:
            print(
                "Document: ",
                doc.metadata.get("Header 2", ""),
                doc.metadata.get("Header 3", ""),
                "Score: ",
                score,
            )

        document_dicts = [
            {"metadata": doc.metadata, "page_content": doc.page_content}
            for doc, score in documents
        ]

    except Exception as e:
        print("Error: ", e)

    return {"data": document_dicts}
