from django.contrib import admin
from django.urls import path

from config import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("setup-status/", views.home, name="setup-status"),
]
