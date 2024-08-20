from django.urls import path

from .views import ChatBot, get_documents


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
    path("sentry-debug/", trigger_error),
]
