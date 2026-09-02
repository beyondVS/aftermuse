from django.contrib import admin
from django.urls import include, path

from config import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", views.home, name="home"),
    path("setup-status/", views.home, name="setup-status"),
]
