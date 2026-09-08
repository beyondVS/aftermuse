from django.urls import path

from reflections import views

app_name = "reflections"

urlpatterns = [
    path(
        "readings/<int:reading_id>/start/",
        views.interview_start,
        name="interview_start",
    ),
    path(
        "readings/<int:reading_id>/start/confirm/",
        views.interview_create,
        name="interview_create",
    ),
    path(
        "interviews/<int:interview_id>/",
        views.interview_detail,
        name="interview_detail",
    ),
]
