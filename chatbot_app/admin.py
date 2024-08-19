from django.contrib import admin
from .models import UserChats, ChatHistory, Document
from django.utils.html import format_html


class UserChatsAdmin(admin.ModelAdmin):
    list_display = ("user_id", "chat_id")  # Customize the list display


class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ("chat", "user_query", "bot_response", "shortened_bot_tool_call")
    search_fields = ("user_query", "bot_response")
    raw_id_fields = ("chat",)

    def shortened_bot_tool_call(self, obj):
        return str(obj.bot_tool_call)[:50] if obj.bot_tool_call else "None"

    shortened_bot_tool_call.short_description = "Bot Tool Call"


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "document_link")
    search_fields = ("filename",)

    def document_link(self, obj):
        if obj.document:
            return format_html(
                '<a href="{url}">{filename}</a>',
                url=obj.document.url,
                filename=obj.filename,
            )
        return "No Document"

    document_link.short_description = "Document Link"


# Register your models here
admin.site.register(UserChats, UserChatsAdmin)
admin.site.register(ChatHistory, ChatHistoryAdmin)
admin.site.register(Document, DocumentAdmin)
