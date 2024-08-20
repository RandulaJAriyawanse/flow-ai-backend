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


@method_decorator(csrf_exempt, name="dispatch")
class ChatBot(View):
    """
    Handle POST requests to generate an answer for a given input query.
    Methods:
    - post(request): Processes the input query and returns the generated response.
    - get(request): Retrieves the chat history for a given user_id.
    """

    async def post(self, request):
        try:
            data = json.loads(request.body)
            input_query = data.get("input_query", "")
            user_id = data.get("user_id", "")

            user_chat, created = await sync_to_async(
                lambda: UserChats.objects.get_or_create(user_id=user_id),
                thread_sensitive=True,
            )()

            async def generate_data():
                bot_response = ""
                tool_call = None
                async for chunk in get_answer(question=input_query, user_id=user_id):
                    if type(chunk) != dict:
                        bot_response += chunk
                        yield chunk
                    elif type(chunk) == dict:
                        tool_call = chunk
                        chunk = json.dumps(chunk)
                        yield chunk
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
            history_data = [
                {
                    "chat_id": chat_history["chat__chat_id"],
                    "user_query": chat_history["user_query"],
                    "bot_response": chat_history["bot_response"],
                    "bot_tool_call": chat_history["bot_tool_call"],
                }
                for chat_history in chat_histories
            ]

            return JsonResponse({"chat_history": history_data}, status=200)
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
