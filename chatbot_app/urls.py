from django.urls import path
from .views import ChatBot, get_documents, get_user_documents, FileUploadView


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("chatbot", ChatBot.as_view(), name="chatbot_view"),
    path("documents", get_documents, name="get_documents"),
    path(
        "chatbot/delete_chathistory/<int:user_id>/",
        ChatBot.delete_chat_history,
        name="delete_chathistory",
    ),
    path(
        "user_documents/<int:user_id>/",
        get_user_documents,
        name="get-user-documents",
    ),
    path("upload/<int:user_id>/", FileUploadView.as_view(), name="file-upload"),
    path("sentry-debug/", trigger_error),
]
