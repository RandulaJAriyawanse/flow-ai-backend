from django.urls import path
from .views import login, register, logout, guest

urlpatterns = [
    path("login", login, name="auth.login"),
    path("register", register, name="auth.register"),
    path("logout", logout, name="auth.logout"),
    path("guest", guest, name="auth.guest"),
]
