# from langchain_openai import OpenAIEmbeddings
# from langchain_core.documents import Document
# from langchain_postgres.vectorstores import PGVector
# from langchain_text_splitters import (
#     Language,
#     RecursiveCharacterTextSplitter,
# )
# import os
# import environ
# import json
# import pymupdf
# import pymupdf4llm
# from langchain_text_splitters import MarkdownHeaderTextSplitter
# import time
# from langchain_core.documents import Document
# import re
# from django.db import connection
# from langchain_core.tools import tool
# import hashlib
# from langchain_core.runnables import RunnableConfig


# def get_env(key: str) -> str:
#     env = environ.Env(DEBUG=(bool, False))
#     BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     env_file_path = environ.Env.read_env(os.path.join(BASE_DIR, "chatbot_app", ".env"))
#     return env(key)


# db_engine = "postgresql+psycopg"
# db_name = get_env("DATABASE_NAME")
# db_user = get_env("DATABASE_USER")
# db_password = get_env("DATABASE_PASSWORD")
# db_host = get_env("DATABASE_HOST")
# db_port = get_env("DATABASE_PORT")
# LLAMAINDEX_API_KEY = get_env("OPENAI_API_KEY")

# connection_string = (
#     f"{db_engine}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
# )


# def extract_page_number(dictionaries):
#     st = time.time()
#     pattern = r"\n?<!--PAGE(\d+)-->\n?"

#     combined_documents = []
#     combined_content = ""
#     combined_metadata = None

#     start = 0

#     for item in dictionaries:
#         print("---------------------------------------------------------")
#         content = item.page_content

#         start += 1
#         match = re.search(pattern, content)

#         if match:
#             # print("Match: ", match)
#             # print("Match group: ", match.group(1))
#             page_number = int(match.group(1))
#             item.metadata["page_number"] = page_number
#             cleaned_content = re.sub(pattern, "", content)
#             item.page_content = cleaned_content

#     for i in range(len(dictionaries)):
#         if "page_number" not in dictionaries[i].metadata:
#             # Look ahead in the list to find the next available page_number
#             for j in range(i + 1, len(dictionaries)):
#                 if "page_number" in dictionaries[j].metadata:
#                     # Assign the found page_number to the current item
#                     dictionaries[i].metadata["page_number"] = dictionaries[j].metadata[
#                         "page_number"
#                     ]
#                     break
#     return dictionaries


# def document_to_dict_2(doc):
#     return {
#         "page_content=": doc.page_content,
#         "metadata": doc.metadata,
#     }


# def get_pdf_splits(file, file_name):
#     documents = pymupdf.open(stream=file, filetype="pdf")
#     full_md = ""

#     print("document 1: ", documents[0])
#     print("document 2: ", documents[1].get_text("text"))

#     for page_num in range(len(documents)):
#         print("page_num: ", page_num)
#         md_text = pymupdf4llm.to_markdown(documents, pages=[page_num])
#         full_md += md_text + f"\n<!--PAGE{page_num}-->\n"
#         # print(f"\n<!--PAGE{page_num}-->\n")

#     headers_to_split_on = [
#         ("#", "Header 1"),
#         ("##", "Header 2"),
#         ("###", "Header 3"),
#     ]
#     text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on, strip_headers=False)
#     md_splits = text_splitter.split_text(full_md)

#     # print("splits: ", type(md_splits))
#     # print("split: ", md_splits[0])
#     # print("type split: ", type(md_splits[0]))
#     md_splits = extract_page_number(md_splits)

#     for doc in md_splits:
#         doc.metadata["file_name"] = file_name[:-4]
#         doc.metadata["user_store"] = "true"

#     # documents_serializable = [document_to_dict_2(doc) for doc in md_splits]
#     # with open(f"scripts/user_0109_json/{file[:-4]}.json", "w") as f:
#     #     json.dump(documents_serializable, f, indent=4)

#     return md_splits


# def get_pdf_stores():
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT name FROM langchain_pg_collection")
#         names = [row[0] for row in cursor.fetchall()]
#         return names


# def create_vectorstore(user_id, file, file_name, pdf_store_id):
#     # parser = LlamaParse(
#     #     api_key=LLAMAINDEX_API_KEY,
#     #     result_type="markdown",
#     #     use_vendor_multimodal_model=True,
#     #     vendor_multimodal_model_name="openai-gpt-4o-mini",
#     # )
#     print("creatng vectorstore")
#     store_list = get_pdf_stores()
#     # print("pdf_store_id user_rag: ", pdf_store_id)
#     try:
#         # if pdf_store_id not in store_list:
#         print("-------------------start splits----------------------------")
#         splits = get_pdf_splits(file, file_name)
#         print("splits: ", splits)
#         print("-------------------end splits----------------------------")
#         print("pdf_store_id: ", pdf_store_id)

#         vectorstore = PGVector.from_documents(
#             embedding=OpenAIEmbeddings(
#                 model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
#             ),
#             documents=splits,
#             connection=connection_string,
#             collection_name=pdf_store_id,
#             pre_delete_collection=False,
#         )
#         print("vectorstore  created", vectorstore)

#     except Exception as e:
#         print("create_vectorstore error: ", e)


# # -------------------------get_documents-------------------------


# def get_existing_vectorstore(collection):
#     print("get_existing_vectorstore")
#     # print("collection: ", collection)
#     vectorstore = PGVector(
#         embeddings=OpenAIEmbeddings(
#             model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
#         ),
#         collection_name=collection,
#         connection=connection_string,
#     )

#     return vectorstore


# @tool
# async def get_user_file_information(question: str, *, config: RunnableConfig):
#     """
#     Consult if you think the user is asking a question about their own file
#     """
#     # collection = "AASB_FULL_2808"
#     configuration = config.get("configurable", {})
#     pdf_store_id = configuration.get("pdf_store_id", None)
#     print("get_user_file_information")
#     # print("pdf_store_id: ", pdf_store_id)
#     # print("question: ", question)

#     vectorstore = get_existing_vectorstore(pdf_store_id)
#     # filter={"file_name": {"$eq": "AASB2 Share-based Payment"}}
#     documents = vectorstore.similarity_search_with_score(
#         question,
#         k=3,
#     )

#     document_dicts = [
#         {"metadata": doc.metadata, "page_content": doc.page_content}
#         for doc, score in documents
#     ]

#     return {"data": document_dicts}


# # "In the AASB comparison with IFRS, tell me how to identify australian specific paragraphs"
