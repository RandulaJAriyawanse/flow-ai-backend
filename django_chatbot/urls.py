from django.contrib import admin
from django.urls import path, include, re_path


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("chatbot_app.urls"), name="api.route"),
    path("auth/", include("authentication.urls"), name="auth.route"),
    path("sentry-debug/", trigger_error),
]
