from django.urls import path

from books import views

app_name = "books"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("select/", views.select, name="select"),
]
