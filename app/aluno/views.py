from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from app.htmx import HtmxModalDeleteMixin, HtmxModalUpdateMixin

from .models import Student


class StudentListView(ListView):
    model = Student
    template_name = "aluno/student_list.html"
    context_object_name = "students"
    ordering = ["name"]
    paginate_by = 5
    extra_context = {"title": "Alunos"}

    def get_queryset(self):
        queryset = super().get_queryset().select_related("course")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(rgm__icontains=search)
                | Q(email__icontains=search)
                | Q(course__name__icontains=search)
            )
        return queryset


class StudentCreateView(CreateView):
    model = Student
    fields = ["name", "rgm", "email", "course"]
    template_name = "form.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Novo aluno"}


class StudentUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Student
    fields = ["name", "rgm", "email", "course"]
    template_name = "form.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Editar aluno"}
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "aluno/partials/student_row.html"
    modal_object_name = "student"
    modal_row_id_prefix = "student-row"


class StudentDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Student
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Excluir aluno"}
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "student-row"