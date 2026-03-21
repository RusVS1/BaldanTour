from django.urls import path

from . import api

urlpatterns = [
    path("register/", api.RegisterAPI.as_view(), name="api_register"),
    path("login/", api.LoginAPI.as_view(), name="api_login"),
    path("logout/", api.LogoutAPI.as_view(), name="api_logout"),
    path("me/", api.MeAPI.as_view(), name="api_me"),
    path("status/", api.AuthStatusAPI.as_view(), name="api_auth_status"),
]

