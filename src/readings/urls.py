from django.urls import path

from readings import views

app_name = "readings"

urlpatterns = [
    path("books/<int:book_id>/", views.book_entry, name="book_entry"),
    path("books/<int:book_id>/create/", views.create, name="create"),
    path("<int:reading_id>/", views.detail, name="detail"),
    path("<int:reading_id>/reread/", views.reread, name="reread"),
    path("<int:reading_id>/state/", views.change_state, name="change_state"),
]
