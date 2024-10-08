# Generated by Django 5.0.7 on 2024-08-31 13:00

import chatbot_app.models
import chatbot_app.utils
import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot_app", "0004_chathistory_created_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserDocument",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "document",
                    models.FileField(
                        blank=True,
                        null=True,
                        storage=chatbot_app.utils.CustomS3Boto3Storage(),
                        upload_to=chatbot_app.models.user_directory_path,
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["pdf", "doc", "docx"]
                            )
                        ],
                    ),
                ),
                ("filename", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Document",
                "verbose_name_plural": "User Documents",
            },
        ),
        migrations.AddConstraint(
            model_name="userdocument",
            constraint=models.UniqueConstraint(
                fields=("user", "filename"), name="unique_user_document"
            ),
        ),
    ]
