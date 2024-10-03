import uuid
from django.db import models
from django.contrib.auth.models import User
from .utils import document_path, CustomS3Boto3Storage
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
import hashlib


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

    FOLDER_CHOICES = [
        ("aasb", "AASB"),
        ("annual_reports", "Annual Reports"),
    ]

    def document_upload_path(instance, filename):
        return f"documents/{instance.folder}/{filename}"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    folder = models.CharField(
        max_length=100, choices=FOLDER_CHOICES, null=True, blank=True
    )
    document = models.FileField(
        upload_to=document_upload_path,
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

    def delete(self, *args, **kwargs):
        if self.document:
            self.document.delete(save=False)  # Delete the file from S3
        super().delete(*args, **kwargs)


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/user_<id>/<filename>
    return f"user_documents/user_{instance.user.id}/{filename}"


class UserDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_documents"
    )
    document = models.FileField(
        upload_to=user_directory_path,
        storage=CustomS3Boto3Storage(),
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
        null=True,
        blank=True,
    )
    filename = models.CharField(max_length=255, null=True, blank=True)
    pdf_store_id = models.CharField(
        max_length=64, editable=False, null=True, blank=True
    )

    class Meta:
        verbose_name = _("User Document")
        verbose_name_plural = _("User Documents")
        # Optionally, you can add a constraint to ensure a user can't have duplicate filenames
        constraints = [
            models.UniqueConstraint(
                fields=["user", "filename"], name="unique_user_document"
            )
        ]

    def delete(self, *args, **kwargs):
        if self.document:
            self.document.delete(save=False)  # Delete the file from S3
        super().delete(*args, **kwargs)

    # # adds onto the default save method
    # def save(self, *args, **kwargs):
    #     if self.user and self.document:
    #         user_id_bytes = str(self.user.id).encode("utf-8")
    #         file_content = self.document.read()
    #         combined_bytes = user_id_bytes + file_content
    #         self.pdf_store_id = hashlib.sha256(
    #             combined_bytes
    #         ).hexdigest()  # Or use md5 or other hash algorithms as needed
    #         self.document.seek(0)  # Reset the file pointer to the beginning of the file

    #     super().save(*args, **kwargs)
