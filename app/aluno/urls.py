from django.urls import path

from .views import (
    StudentCreateView,
    StudentDeleteView,
    StudentListView,
    StudentUpdateView,
)

app_name = "aluno"

urlpatterns = [
    path("", StudentListView.as_view(), name="student_list"),
    path("novo/", StudentCreateView.as_view(), name="student_create"),
    path("<int:pk>/editar/", StudentUpdateView.as_view(), name="student_update"),
    path("<int:pk>/excluir/", StudentDeleteView.as_view(), name="student_delete"),
]