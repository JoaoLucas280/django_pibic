from django.urls import path

from .views import (
    EnrollmentCreateView,
    EnrollmentDeleteView,
    EnrollmentUpdateView,
    ReportCardView,
    StudentCreateView,
    StudentDeleteView,
    StudentDetailView,
    StudentListView,
    StudentUpdateView,
)

app_name = "aluno"

urlpatterns = [
    path("", StudentListView.as_view(), name="student_list"),
    path("novo/", StudentCreateView.as_view(), name="student_create"),
    path("<int:pk>/", StudentDetailView.as_view(), name="student_detail"),
    path("<int:pk>/boletim/", ReportCardView.as_view(), name="report_card"),
    path("<int:pk>/editar/", StudentUpdateView.as_view(), name="student_update"),
    path("<int:pk>/excluir/", StudentDeleteView.as_view(), name="student_delete"),
    path("<int:pk>/matricular/", EnrollmentCreateView.as_view(), name="enrollment_create"),
    path("matriculas/<int:pk>/editar/", EnrollmentUpdateView.as_view(), name="enrollment_update"),
    path("matriculas/<int:pk>/excluir/", EnrollmentDeleteView.as_view(), name="enrollment_delete"),
]
