from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)
import os
import environ
import json
import pymupdf
import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter
import time
from langchain_core.documents import Document


def document_to_dict(doc):
    return {
        "id": doc.id_,
        "text": doc.text,
        "metadata": doc.metadata,
        "embedding": (
            None if doc.embedding is None else doc.embedding.tolist()
        ),  # Assuming embedding is an array
    }


def document_to_dict_2(doc):
    return {
        "page_content=": doc.page_content,
        "metadata": doc.metadata,
    }


def get_env(key: str) -> str:
    env = environ.Env(DEBUG=(bool, False))
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file_path = environ.Env.read_env(os.path.join(BASE_DIR, "chatbot_app", ".env"))
    return env(key)


import re


def combine_contents(dictionaries):
    combined_content = ""
    combined_metadata = None
    remaining_documents = []
    insert_index = None

    for index, doc in enumerate(dictionaries):
        header_2 = doc.metadata.get("Header 2", "")
        if header_2 == "Contents":
            if insert_index is None:
                insert_index = index
            cleaned_content = doc.page_content.replace("###", "").strip()
            combined_content += cleaned_content + "\n"
            if not combined_metadata:
                combined_metadata = {
                    "Header 1": doc.metadata["Header 1"],
                    "Header 2": doc.metadata["Header 2"],
                }
        else:
            remaining_documents.append(doc)

    if combined_content:
        combined_document = Document(
            page_content=combined_content.strip(),
            metadata=combined_metadata,
        )
        # Insert the combined document back into the correct position
        remaining_documents.insert(insert_index, combined_document)

    return remaining_documents


def extract_page_number(dictionaries):
    st = time.time()
    pattern = r"\n?<!--PAGE(\d+)-->\n?"

    combined_documents = []
    combined_content = ""
    combined_metadata = None

    start = 0

    for item in dictionaries:
        print("------------------------()---------------------------------")
        content = item.page_content

        start += 1
        if start < 20:
            print("Content: ", content)

        match = re.search(pattern, content)

        if match:
            print("Match: ", match)
            print("Match group: ", match.group(1))
            page_number = int(match.group(1))
            item.metadata["page_number"] = page_number
            cleaned_content = re.sub(pattern, "", content)
            item.page_content = cleaned_content

    for i in range(len(dictionaries)):
        if "page_number" not in dictionaries[i].metadata:
            # Look ahead in the list to find the next available page_number
            for j in range(i + 1, len(dictionaries)):
                if "page_number" in dictionaries[j].metadata:
                    # Assign the found page_number to the current item
                    dictionaries[i].metadata["page_number"] = dictionaries[j].metadata[
                        "page_number"
                    ]
                    break
    return dictionaries


db_engine = "postgresql+psycopg"
db_name = get_env("DATABASE_NAME")
db_user = get_env("DATABASE_USER")
db_password = get_env("DATABASE_PASSWORD")
db_host = get_env("DATABASE_HOST")
db_port = get_env("DATABASE_PORT")

connection_string = (
    f"{db_engine}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)


# def get_pdf_splits(parser, file):
#     documents = parser.load_data(f"scripts/AASB_Test_Files/{file}")
#     documents_serializable = [document_to_dict(doc) for doc in documents]
#     print(file[:-4])
#     with open(f"scripts/{file[:-4]}.json", "w") as f:
#         json.dump(documents_serializable, f, indent=4)

# pdf_documents = []

# for page_num in range(len(documents)):
#     page = documents[page_num]
#     page_text = page.text
#     pdf_documents.append(
#         Document(
#             page_content=page_text,
#             metadata={"page_number": page_num, "file_name": file[:-4]},
#         )
#     )

#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1400, chunk_overlap=200)
#     splits = text_splitter.split_documents(pdf_documents)
#     return splits


# def create_vectorstore():
#     parser = LlamaParse(
#         api_key="llx-f3z3xAVeycZDYauOLi9Gzo0H9RgXJn54xFIGE2uR3OG6Kzba",
#         result_type="markdown",
#     )
#     for file in os.listdir("scripts/AASB_Files"):
#         if file.endswith(".pdf"):
#             splits = get_pdf_splits(parser, file)
#             vectorstore = PGVector.from_documents(
#                 embedding=OpenAIEmbeddings(),
#                 documents=splits,
#                 connection=connection_string,
#                 collection_name="AASB",
#                 pre_delete_collection=False,
#             )
#             print("success: ", file)


# create_vectorstore()


def get_pdf_splits(file):

    documents = pymupdf.open(f"scripts/AASB_Files/{file}")
    # pdf_documents = []
    # pdf_documents_json = []
    full_md = ""

    for page_num in range(len(documents)):
        md_text = pymupdf4llm.to_markdown(documents, pages=[page_num])
        full_md += md_text + f"\n<!--PAGE{page_num}-->\n"
        print(f"\n<!--PAGE{page_num}-->\n")
        # pdf_documents.append(
        #     Document(
        #         page_content=md_text,
        #         metadata={"page_number": page_num, "file_name": file[:-4]},
        #     )
        # )
        # documents_serializable = [document_to_dict_2(doc) for doc in pdf_documents]
        # with open(f"scripts/{file[:-4]}_pymullm_by_page.json", "w") as f:
        #     json.dump(pdf_documents_json, f, indent=4)

    # checks if bold and that next line isn't bold, and that line starts with a capital
    # could be improved by only checking for for the capital and bold, to account for 2 line headers
    pattern = r"(?<=\n)\*\*([A-Z].+?)\*\*\s*\n(?!\*\*)"
    header_3_md = re.sub(pattern, r"### \1\n", full_md)

    # # convert space space numbers to header 4
    # pattern = r"(\s+\n)(\d+)"
    # header_4_md = re.sub(pattern, r"\1#### \2", header_3_md)

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        # ("####", "Header 4"),
    ]
    text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on, strip_headers=False)
    md_splits = text_splitter.split_text(header_3_md)

    print("splits: ", type(md_splits))
    print("split: ", md_splits[0])
    print("type split: ", type(md_splits[0]))

    # documents_serializable = [document_to_dict_2(doc) for doc in md_splits]
    # with open(f"scripts/{file[:-4]}_pymullm_by_page_mdsplitter_splits.json", "w") as f:
    #     json.dump(documents_serializable, f, indent=4)

    md_splits = combine_contents(md_splits)
    md_splits = extract_page_number(md_splits)

    for doc in md_splits:
        doc.metadata["file_name"] = file[:-4]
        # header_2 = doc.metadata.get("Header 2", None)
        # if header_2:
        #     doc.page_content = f"##{doc.metadata['Header 2']} \n{doc.page_content}"

    documents_serializable = [document_to_dict_2(doc) for doc in md_splits]
    with open(f"scripts/1808_json/{file[:-4]}.json", "w") as f:
        json.dump(documents_serializable, f, indent=4)

    # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
    # splits = text_splitter.split_documents(md_splits)
    # documents_serializable = [document_to_dict_2(doc) for doc in splits]
    # with open(f"scripts/{file[:-4]}_pymu_md_recursive_header_3.json", "w") as f:
    #     json.dump(documents_serializable, f, indent=4)
    return md_splits


def create_vectorstore():
    # parser = LlamaParse(
    #     api_key="llx-f3z3xAVeycZDYauOLi9Gzo0H9RgXJn54xFIGE2uR3OG6Kzba",
    #     result_type="markdown",
    #     use_vendor_multimodal_model=True,
    #     vendor_multimodal_model_name="openai-gpt-4o-mini",
    # )

    for file in os.listdir("scripts/AASB_Files"):
        if file.endswith(".pdf"):
            print(file)
            splits = get_pdf_splits(file)
            vectorstore = PGVector.from_documents(
                embedding=OpenAIEmbeddings(model="text-embedding-3-large"),
                documents=splits,
                connection=connection_string,
                collection_name="AASB_1908",
                pre_delete_collection=False,
            )
            print("success: ", file)


create_vectorstore()


# import pymupdf4llm
# import pathlib

# md_text = pymupdf4llm.to_markdown("scripts/AASB_Files/AASB2 Share-based Payment.pdf")
# pathlib.Path("pymu_aasb2.md").write_bytes(md_text.encode())
