import sentry_sdk
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework import status
from .serializer import UserSerializer
import uuid
from datetime import datetime


@api_view(["POST"])
def login(request):
    """
    Handle user login.
    Args:
    - request: HTTP request with 'email' and 'password'.
    Returns:
    - 200 OK: Token and user data if credentials are valid.
    - 404 NOT FOUND: If user is not found or password is incorrect.
    - 500 INTERNAL SERVER ERROR: For server errors.
    """
    try:
        user = get_object_or_404(User, email=request.data["email"])
        print("Login...")
        if not user.check_password(request.data["password"]):
            return Response("missing user", status=status.HTTP_404_NOT_FOUND)
        existing_token = Token.objects.filter(user=user).first()
        if existing_token:
            return Response(
                {"error": "User already logged in", "token": existing_token.key},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(user)
        return Response({"token": token.key, "user": serializer.data})
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return Response(
            {"error": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def register(request):
    """
    Handle user registration.
    Args:
    - request: HTTP request with user data.
    Returns:
    - 201 CREATED: Token and user data if registration is successful.
    - 400 BAD REQUEST: If provided data is invalid.
    - 500 INTERNAL SERVER ERROR: For server errors.
    """
    try:
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(username=request.data["username"])
            user.set_password(request.data["password"])
            user.save()
            token = Token.objects.create(user=user)
            return Response({"token": token.key, "user": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return Response(
            {"error": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def logout(request):
    """
    Handle user logout.
    Args:
    - request: HTTP request with the user's token.
    Returns:
    - 204 NO CONTENT: If the token is successfully deleted.
    - 400 BAD REQUEST: If the token is invalid.
    - 500 INTERNAL SERVER ERROR: For server errors.
    """
    try:
        token = get_object_or_404(Token, key=request.headers.get("Authorization"))
        if token:
            token.delete()
            return Response(
                {"detail": "Token deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print("Logout error: ", e)
        return Response(
            {"error": f"User already logged out: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def guest(request):
    """
    Automatically creates a unique user for each login request and returns user details and a token.
    """
    try:
        unique_username = (
            f"guest_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        )
        user = User.objects.create_user(username=unique_username)
        token = Token.objects.create(user=user)
        serializer = UserSerializer(user)
        return Response({"token": token.key, "user": serializer.data})

    except Exception as e:
        # Log the exception
        sentry_sdk.capture_exception(e)
        print("Guest login error: ", e)
        return Response(
            {"error": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
