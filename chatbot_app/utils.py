import os
import environ
from storages.backends.s3boto3 import S3Boto3Storage


def get_env(key: str) -> str:
    env = environ.Env(DEBUG=(bool, False))
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file_path = environ.Env.read_env(os.path.join(BASE_DIR, "chatbot_app", ".env"))
    return env(key)


def document_path(instance, filename):
    """Function to generate the path for uploaded documents"""
    ext = filename.split(".")[-1]
    # Generate a unique filename
    filename = f"{instance.id}.{ext}"
    return os.path.join("documents", filename)


class CustomS3Boto3Storage(S3Boto3Storage):
    """Custom S3 storage class to delete files from S3 when the corresponding object is deleted"""

    def delete(self, name):
        """Doc"""
        if self.exists(name):
            self.bucket.delete_objects(Delete={"Objects": [{"Key": name}]})
