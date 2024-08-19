import uuid
from django.db import models
from .utils import document_path, CustomS3Boto3Storage
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


class UserChats(models.Model):
    user_id = models.IntegerField()
    chat_id = models.AutoField(primary_key=True)

    def __str__(self) -> str:
        return f"UserID = {self.user_id}, ChatID = {self.chat_id}"


class ChatHistory(models.Model):
    chat = models.ForeignKey(
        UserChats, on_delete=models.CASCADE, related_name="chat_histories"
    )
    user_query = models.TextField(blank=False)
    bot_response = models.TextField(blank=False)
    bot_tool_call = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"ChatID = {self.chat.id}, UserQuery = {self.user_query[:20]}, BotResponse = {self.bot_response[:20]}"


class Document(models.Model):
    """Doc"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.FileField(
        upload_to="documents/",
        storage=CustomS3Boto3Storage(),
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
        null=True,
        blank=True,
    )
    filename = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        """Doc"""

        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
