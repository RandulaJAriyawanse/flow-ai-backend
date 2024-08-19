from django.urls import path

from .views import ChatBot, get_documents

urlpatterns = [
    path("chatbot", ChatBot.as_view(), name="chatbot_view"),
    path("documents", get_documents, name="get_documents"),
    path(
        "chatbot/delete_chathistory/<int:user_id>/",
        ChatBot.delete_chat_history,
        name="delete_chathistory",
    ),
]
