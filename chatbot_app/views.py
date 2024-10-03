from django.http import JsonResponse, StreamingHttpResponse
from .models import UserChats, ChatHistory
import sentry_sdk
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .langchain_helper import get_answer
import json
from .models import Document
from asgiref.sync import sync_to_async
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserDocument
from .serializers import UserDocumentSerializer
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db import connection
import hashlib
from rest_framework.permissions import AllowAny
import json

from chatbot_app.llm_tools.user_rag import create_vectorstore


@method_decorator(csrf_exempt, name="dispatch")
class ChatBot(View):
    """
    Handle POST requests to generate an answer for a given input query.
    Methods:
    - post(request): Processes the input query and returns the generated response.
    - get(request): Retrieves the chat history for a given user_id.
    """

    # authentication_classes = []  # No authentication required
    # permission_classes = [AllowAny]

    async def post(self, request):
        try:
            data = json.loads(request.body)
            input_query = data.get("input_query", "")
            user_id = data.get("user_id", "")
            pdf_store_id = data.get("pdf_store_id", None)
            print("pdf_store_id: ", pdf_store_id)

            user_chat, created = await sync_to_async(
                lambda: UserChats.objects.get_or_create(user_id=user_id),
                thread_sensitive=True,
            )()

            async def generate_data():
                bot_response = ""
                tool_call = None
                async for chunk in get_answer(
                    question=input_query,
                    user_id=user_id,
                    pdf_store_id=pdf_store_id,
                ):
                    # print("------------------------------------------------")
                    # print("chunk: ", chunk)
                    if chunk["type"] == "chat_response":
                        bot_response += chunk["data"]
                        yield json.dumps(chunk) + "\n"
                    elif chunk["type"] == "tool_response":
                        tool_call = chunk
                        chunk = json.dumps(chunk)
                        yield chunk + "\n"

                await sync_to_async(
                    lambda: ChatHistory.objects.create(
                        chat=user_chat,
                        user_query=input_query,
                        bot_response=bot_response,
                        bot_tool_call=tool_call,
                    ),
                    thread_sensitive=True,
                )()

            return StreamingHttpResponse(generate_data(), content_type="text/plain")
        except json.JSONDecodeError:
            sentry_sdk.capture_exception(e)
            return JsonResponse({"errors": "Invalid JSON"}, status=400)

        except Exception as e:
            sentry_sdk.capture_exception(e)
            return JsonResponse({"errors": str(e)}, status=500)

    async def get(self, request):
        try:
            user_id = request.GET.get("user_id", None)
            if not user_id:
                return JsonResponse({"errors": "Missing user_id parameter"}, status=400)

            latest_chat = sync_to_async(
                UserChats.objects.filter(user_id=user_id).latest, thread_sensitive=True
            )
            user_chat = await latest_chat("chat_id")
            chat_histories_query = (
                ChatHistory.objects.filter(chat=user_chat)
                .select_related("chat")
                .order_by("created_at")
            )
            chat_histories = await sync_to_async(
                lambda: list(
                    chat_histories_query.values(
                        "chat__chat_id",
                        "user_query",
                        "bot_response",
                        "bot_tool_call",
                    )
                )
            )()
            return JsonResponse({"chat_history": chat_histories}, status=200)
        except UserChats.DoesNotExist:
            return JsonResponse({"errors": "No chats found for this user"}, status=404)
        except Exception as e:
            print(e)
            sentry_sdk.capture_exception(e)
            return JsonResponse({"errors": str(e)}, status=500)

    @staticmethod
    @csrf_exempt
    async def delete_chat_history(request, user_id):
        try:
            user_chats = UserChats.objects.filter(user_id=user_id)

            if await sync_to_async(user_chats.exists)():
                await sync_to_async(
                    user_chats.delete
                )()  # This will also delete all related ChatHistory entries due to cascade delete
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Chat history deleted successfully",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "No chat history found for this user",
                    },
                    status=404,
                )
        except Exception as e:
            print("An error occurred: ", e)
            sentry_sdk.capture_exception(e)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


@api_view(["GET"])
def get_documents(request):
    try:
        # Get the folder from query params
        folder = request.GET.get("folder")

        # Filter documents by folder, if provided
        if folder:
            documents = Document.objects.filter(folder=folder)
        else:
            documents = Document.objects.all()

        data = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "document_url": doc.document.url if doc.document else None,
            }
            for doc in documents
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return JsonResponse({"errors": str(e)}, status=500)


@api_view(["GET"])
def get_user_documents(request, user_id):
    try:
        user = get_object_or_404(User, pk=user_id)
        documents = UserDocument.objects.filter(user=user)
        data = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "document_url": doc.document.url if doc.document else None,
                "pdf_store_id": doc.pdf_store_id,
            }
            for doc in documents
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        print(e)
        return JsonResponse({"errors": str(e)}, status=500)


class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, pk=user_id)
            uploaded_file = request.FILES.get("document").read()
            file_name = request.FILES.get("document").name
            serializer = UserDocumentSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    user_id_bytes = str(user_id).encode("utf-8")
                    combined_bytes = user_id_bytes + uploaded_file
                    pdf_store_id = hashlib.sha256(combined_bytes).hexdigest()
                    create_vectorstore(user_id, uploaded_file, file_name, pdf_store_id)
                    serializer.save(user=user, pdf_store_id=pdf_store_id)
                    return Response(serializer.data)
                except IntegrityError as e:
                    if "unique_user_document" in str(e):
                        print(
                            "Document with the same name already exists for this user.",
                            e,
                        )
                        existing_document = UserDocument.objects.get(
                            user=user, filename=file_name
                        )

                        return Response(UserDocumentSerializer(existing_document).data)
                    else:
                        print("An unexpected database error occurred.", e)
                        return Response(
                            {"error": "An unexpected database error occurred."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
            else:
                print("serializer error: ", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            print("Validation error: ", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("An unexpected error occurred.", e)
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
