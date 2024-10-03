from rest_framework import serializers
from .models import UserDocument


class UserDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocument
        fields = ["document", "filename", "pdf_store_id"]

    def validate_document(self, value):
        if value.name.split(".")[-1].lower() != "pdf":
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value
