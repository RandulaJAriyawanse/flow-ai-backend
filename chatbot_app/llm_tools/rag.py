from django.db import connection
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from typing import Optional
from chatbot_app.utils import get_env
import os
import time

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


@tool
async def get_AASB_information(
    question,
):
    """
    Consult the AASB standards for any question regarding Australian accounting standards.
    """
    st = time.time()
    collection = "AASB_FULL_2808"
    vectorstore = get_existing_vectorstore(collection)
    # filter={"file_name": {"$eq": "AASB2 Share-based Payment"}}
    documents = vectorstore.similarity_search_with_score(
        question,
        k=3,
    )
    print("Retrieve time: ", time.time() - st)

    document_dicts = [
        {"metadata": doc.metadata, "page_content": doc.page_content}
        for doc, score in documents
    ]
    print("Full RAG time: ", time.time() - st)

    return {"data": document_dicts}


# "In the AASB comparison with IFRS, tell me how to identify australian specific paragraphs"
