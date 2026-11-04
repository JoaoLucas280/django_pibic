from django.urls import path

from .views import (
    CourseCreateView,
    CourseDeleteView,
    CourseDetailView,
    CourseListView,
    CourseUpdateView,
    DisciplineCreateView,
    DisciplineDeleteView,
    DisciplineListView,
    DisciplineUpdateView,
    SemesterCreateView,
    SemesterDeleteView,
    SemesterDetailView,
    SemesterListView,
    SemesterUpdateView,
)

app_name = "curso"

urlpatterns = [
    path("", CourseListView.as_view(), name="course_list"),
    path("novo/", CourseCreateView.as_view(), name="course_create"),
    path("<int:pk>/", CourseDetailView.as_view(), name="course_detail"),
    path("<int:pk>/editar/", CourseUpdateView.as_view(), name="course_update"),
    path("<int:pk>/excluir/", CourseDeleteView.as_view(), name="course_delete"),
    path("disciplinas/", DisciplineListView.as_view(), name="discipline_list"),
    path(
        "disciplinas/nova/",
        DisciplineCreateView.as_view(),
        name="discipline_create",
    ),
    path(
        "disciplinas/<int:pk>/editar/",
        DisciplineUpdateView.as_view(),
        name="discipline_update",
    ),
    path(
        "disciplinas/<int:pk>/excluir/",
        DisciplineDeleteView.as_view(),
        name="discipline_delete",
    ),
    path("semestres/", SemesterListView.as_view(), name="semester_list"),
    path("semestres/novo/", SemesterCreateView.as_view(), name="semester_create"),
    path(
        "semestres/<int:pk>/",
        SemesterDetailView.as_view(),
        name="semester_detail",
    ),
    path(
        "semestres/<int:pk>/editar/",
        SemesterUpdateView.as_view(),
        name="semester_update",
    ),
    path(
        "semestres/<int:pk>/excluir/",
        SemesterDeleteView.as_view(),
        name="semester_delete",
    ),
]