from django import forms
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from app.htmx import HtmxModalDeleteMixin, HtmxModalUpdateMixin

from .models import Course, Discipline, Semester



class CourseListView(ListView):
    model = Course
    template_name = "curso/course_list.html"
    context_object_name = "courses"
    ordering = ["name"]
    paginate_by = 5
    extra_context = {"title": "Cursos"}

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class CourseDetailView(DetailView):
    model = Course
    template_name = "curso/course_detail.html"
    context_object_name = "course"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("semesters__disciplines")


class CourseCreateView(CreateView):
    model = Course
    fields = ["name", "duration_semesters"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Novo curso"}


class CourseUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Course
    fields = ["name", "duration_semesters"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Editar curso"}
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "curso/partials/course_row.html"
    modal_object_name = "course"
    modal_row_id_prefix = "course-row"


class CourseDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Course
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Excluir curso"}
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "course-row"


class DisciplineListView(ListView):
    model = Discipline
    template_name = "curso/discipline_list.html"
    context_object_name = "disciplines"
    ordering = ["name"]
    paginate_by = 5
    extra_context = {"title": "Disciplinas"}

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        return queryset


class DisciplineCreateView(CreateView):
    model = Discipline
    fields = ["name", "code", "class_load"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Nova disciplina"}


class DisciplineUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Discipline
    fields = ["name", "code", "class_load"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Editar disciplina"}
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "curso/partials/discipline_row.html"
    modal_object_name = "discipline"
    modal_row_id_prefix = "discipline-row"


class DisciplineDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Discipline
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Excluir disciplina"}
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "discipline-row"

class SemesterListView(ListView):
    model = Semester
    template_name = "curso/semester_list.html"
    context_object_name = "semesters"
    ordering = ["course__name", "number"]
    paginate_by = 5
    extra_context = {"title": "Semestres"}

    def get_queryset(self):
        queryset = super().get_queryset().select_related("course")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(course__name__icontains=search)
                | Q(disciplines__name__icontains=search)
                | Q(disciplines__code__icontains=search)
            ).distinct()
        return queryset


class SemesterDetailView(DetailView):
    model = Semester
    template_name = "curso/semester_detail.html"
    context_object_name = "semester"

    def get_queryset(self):
        return super().get_queryset().select_related("course").prefetch_related(
            "disciplines"
        )


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["course", "number", "disciplines"]
        widgets = {"disciplines": forms.CheckboxSelectMultiple}


class SemesterCreateView(CreateView):
    model = Semester
    form_class = SemesterForm
    template_name = "form.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Novo semestre"}


class SemesterUpdateView(UpdateView):
    model = Semester
    form_class = SemesterForm
    template_name = "form.html"
    success_url = reverse_lazy("curso:semester_list")
    extra_context = {"title": "Editar semestre"}

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["curso/partials/semester_modal_form.html"]
        return super().get_template_names()

    def form_valid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            self.object = form.save()
            response = render(
                self.request,
                "curso/partials/semester_card.html",
                {"semester": self.object},
            )
            response["HX-Retarget"] = f"#semester-card-{self.object.pk}"
            response["HX-Reswap"] = "outerHTML"
            response["HX-Trigger-After-Swap"] = "semesterUpdated"
            return response
        return super().form_valid(form)


class SemesterDeleteView(DeleteView):
    model = Semester
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("curso:semester_list")
    extra_context = {"title": "Excluir semestre"}