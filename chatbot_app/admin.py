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
    # Add 'folder' to the list_display so it's shown in the admin list view
    list_display = ("id", "filename", "folder", "document_link")

    # Allow 'folder' to be searched alongside 'filename'
    search_fields = ("filename", "folder")

    # Allow admins to filter documents by folder
    list_filter = ("folder",)

    # Override form fields to include the folder selection/input
    fields = ("folder", "filename", "document")

    # Add the document link to allow easy access to the file
    def document_link(self, obj):
        if obj.document:
            return format_html(
                '<a href="{url}" target="_blank">{filename}</a>',
                url=obj.document.url,
                filename=obj.filename,
            )
        return "No Document"

    document_link.short_description = "Document Link"


# Register your models here
admin.site.register(UserChats, UserChatsAdmin)
admin.site.register(ChatHistory, ChatHistoryAdmin)
admin.site.register(Document, DocumentAdmin)
