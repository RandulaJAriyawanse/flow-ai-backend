# Generated by Django 5.0.7 on 2024-08-12 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chathistory',
            name='bot_tool_call',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
