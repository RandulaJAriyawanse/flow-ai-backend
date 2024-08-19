# Generated by Django 5.0.7 on 2024-08-05 10:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UserChats",
            fields=[
                ("user_id", models.IntegerField()),
                ("chat_id", models.AutoField(primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name="ChatHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user_query", models.TextField()),
                ("bot_response", models.TextField()),
                (
                    "chat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_histories",
                        to="chatbot_app.userchats",
                    ),
                ),
            ],
        ),
    ]
