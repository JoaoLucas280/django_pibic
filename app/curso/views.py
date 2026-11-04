from django import forms
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from app.htmx import HtmxModalDeleteMixin, HtmxModalUpdateMixin, SuccessFeedbackMixin

from .models import Course, Discipline, Semester



def dashboard(request):
    from aluno.models import Student

    stats = [
        ("Cursos", Course.objects.count(), "curso:course_list"),
        ("Semestres", Semester.objects.count(), "curso:course_list"),
        ("Disciplinas", Discipline.objects.count(), "curso:discipline_list"),
        ("Alunos", Student.objects.count(), "aluno:student_list"),
    ]
    courses = Course.objects.annotate(
        total_students=Count("students", distinct=True),
        total_semesters=Count("semesters", distinct=True),
    ).order_by("-total_students", "name")[:5]
    return render(request, "dashboard.html", {"title": "Início", "stats": stats, "courses": courses})


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


class CourseCreateView(SuccessFeedbackMixin, CreateView):
    model = Course
    fields = ["name", "duration_semesters"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Novo curso"}
    success_message = 'Curso "{object}" cadastrado com sucesso.'


class CourseUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Course
    fields = ["name", "duration_semesters"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Editar curso"}
    success_message = 'Curso "{object}" atualizado com sucesso.'
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "curso/partials/course_row.html"
    modal_object_name = "course"
    modal_row_id_prefix = "course-row"


class CourseDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Course
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("curso:course_list")
    extra_context = {"title": "Excluir curso"}
    success_message = 'Curso "{object}" excluído com sucesso.'
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


class DisciplineCreateView(SuccessFeedbackMixin, CreateView):
    model = Discipline
    fields = ["name", "code", "class_load"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Nova disciplina"}
    success_message = 'Disciplina "{object}" cadastrada com sucesso.'


class DisciplineUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Discipline
    fields = ["name", "code", "class_load"]
    template_name = "form.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Editar disciplina"}
    success_message = 'Disciplina "{object}" atualizada com sucesso.'
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "curso/partials/discipline_row.html"
    modal_object_name = "discipline"
    modal_row_id_prefix = "discipline-row"


class DisciplineDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Discipline
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("curso:discipline_list")
    extra_context = {"title": "Excluir disciplina"}
    success_message = 'Disciplina "{object}" excluída com sucesso.'
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "discipline-row"

class SemesterCourseRedirectMixin:
    """Semestres vivem dentro do curso: salvar, excluir e cancelar voltam pra página do curso."""

    def get_success_url(self):
        return reverse("curso:course_detail", args=[self.object.course_id])

    get_cancel_url = get_success_url


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


class SemesterCreateView(SuccessFeedbackMixin, CreateView):
    model = Semester
    form_class = SemesterForm
    template_name = "form.html"
    extra_context = {"title": "Novo semestre"}
    success_message = 'Semestre "{object}" cadastrado com sucesso.'

    def get_initial(self):
        # Vindo da página do curso (?course=ID), o curso já chega preenchido.
        return {"course": self.request.GET.get("course")}

    def get_success_url(self):
        return reverse("curso:course_detail", args=[self.object.course_id])

    def get_cancel_url(self):
        # Veio de um curso (?course=ID válido)? Cancelar volta pra ele; senão, pra lista de cursos.
        course_id = self.request.GET.get("course", "")
        if course_id.isdigit() and Course.objects.filter(pk=course_id).exists():
            return reverse("curso:course_detail", args=[course_id])
        return reverse("curso:course_list")


class SemesterUpdateView(SemesterCourseRedirectMixin, HtmxModalUpdateMixin, UpdateView):
    model = Semester
    form_class = SemesterForm
    template_name = "form.html"
    extra_context = {"title": "Editar semestre"}
    success_message = 'Semestre "{object}" atualizado com sucesso.'
    modal_form_template_name = "curso/partials/semester_modal_form.html"
    modal_success_template_name = "curso/partials/semester_card.html"
    modal_object_name = "semester"
    modal_row_id_prefix = "semester-card"
    modal_done_event = "semesterUpdated"


class SemesterDeleteView(SemesterCourseRedirectMixin, HtmxModalDeleteMixin, DeleteView):
    model = Semester
    template_name = "confirm_delete.html"
    extra_context = {"title": "Excluir semestre"}
    success_message = 'Semestre "{object}" excluído com sucesso.'
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "semester-card"