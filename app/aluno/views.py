import socket

import segno
from django import forms
from django.core import signing
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from app.htmx import HtmxModalDeleteMixin, HtmxModalUpdateMixin, SuccessFeedbackMixin
from curso.models import Discipline

from .models import APPROVAL_GRADE, MIN_ATTENDANCE, Enrollment, Student

REPORT_CARD_SALT = "aluno.boletim"  # separa estes tokens de outras assinaturas do Django


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def lan_ip():
    """IP deste computador na rede local (o que o celular consegue acessar), ou None se não houver rede."""
    try:
        # UDP "connect" não envia nenhum pacote: só pergunta ao sistema qual interface usaria pra sair
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def report_card_url(request, student):
    """Link público do boletim: ID do aluno assinado com a SECRET_KEY (não dá pra adivinhar nem falsificar)."""
    # ponytail: token não expira nem é revogável; se precisar, adicionar max_age ao loads() ou um campo de versão no aluno
    token = signing.dumps(student.pk, salt=REPORT_CARD_SALT)
    path = reverse("report_card_public", args=[token])
    host, sep, port = request.get_host().rpartition(":")  # "127.0.0.1:8000" -> ("127.0.0.1", ":", "8000")
    if not sep:
        host, port = port, ""  # sem porta: rpartition devolve tudo no último item
    if host in LOOPBACK_HOSTS:
        # Aberto como 127.0.0.1 no PC: no celular esse endereço é o próprio celular. Usa o IP da rede.
        ip = lan_ip()
        if ip:
            return f"{request.scheme}://{ip}{':' + port if port else ''}{path}"
    return request.build_absolute_uri(path)


def qr_svg(url):
    # SVG inline gerado pela biblioteca a partir da nossa própria URL; nítido na tela e no PDF.
    # omitsize=True: usa viewBox em vez de width/height fixos. Sem isso, o CSS que reduz o QR
    # CORTA o desenho (somem 2 dos 3 quadrados de canto) e nenhuma câmera consegue ler.
    # border=4: margem branca mínima exigida pelo padrão QR (ISO/IEC 18004). Preto: máximo contraste.
    return mark_safe(segno.make(url, error="m").svg_inline(scale=4, dark="#000", border=4, omitsize=True))


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


class StudentCreateView(SuccessFeedbackMixin, CreateView):
    model = Student
    fields = ["name", "rgm", "email", "course"]
    template_name = "form.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Novo aluno"}
    success_message = 'Aluno "{object}" cadastrado com sucesso.'


class StudentUpdateView(HtmxModalUpdateMixin, UpdateView):
    model = Student
    fields = ["name", "rgm", "email", "course"]
    template_name = "form.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Editar aluno"}
    success_message = 'Aluno "{object}" atualizado com sucesso.'
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "aluno/partials/student_row.html"
    modal_object_name = "student"
    modal_row_id_prefix = "student-row"


class StudentDeleteView(HtmxModalDeleteMixin, DeleteView):
    model = Student
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("aluno:student_list")
    extra_context = {"title": "Excluir aluno"}
    success_message = 'Aluno "{object}" excluído com sucesso.'
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "student-row"


class StudentDetailView(DetailView):
    model = Student
    template_name = "aluno/student_detail.html"
    context_object_name = "student"

    def get_queryset(self):
        return super().get_queryset().select_related("course")

    def get_context_data(self, **kwargs):
        enrollments = list(self.object.enrollments.select_related("discipline"))
        grades = [e.grade for e in enrollments if e.grade is not None]
        public_url = report_card_url(self.request, self.object)
        return super().get_context_data(
            public_url=public_url,
            qr_code=qr_svg(public_url),
            enrollments=enrollments,
            average=sum(grades) / len(grades) if grades else None,
            approved=sum(e.status == "Aprovado" for e in enrollments),
            approval_grade=APPROVAL_GRADE,
            min_attendance=MIN_ATTENDANCE,
            **kwargs,
        )


class ReportCardView(StudentDetailView):
    # ponytail: PDF via "Salvar como PDF" do navegador (CSS @page A4), sem biblioteca;
    # trocar por WeasyPrint/ReportLab se precisar gerar o arquivo no servidor (ex.: enviar por e-mail)
    template_name = "aluno/report_card.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(issued_at=timezone.localtime(), **kwargs)


class PublicReportCardView(ReportCardView):
    """Boletim aberto pelo QR Code: sem login, só leitura, sem e-mail do aluno."""

    def get_object(self, queryset=None):
        try:
            pk = signing.loads(self.kwargs["token"], salt=REPORT_CARD_SALT)
        except signing.BadSignature:
            raise Http404("Boletim não encontrado ou link inválido.")
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_context_data(self, **kwargs):
        return super().get_context_data(public=True, **kwargs)


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["discipline", "grade", "attendance"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        student = self.instance.student
        # Só disciplinas da grade do curso do aluno, sem as que ele já cursa
        self.fields["discipline"].queryset = (
            Discipline.objects.filter(semesters__course=student.course)
            .exclude(enrollments__student=student)
            .distinct()
            .order_by("name")
        )


class EnrollmentCreateView(SuccessFeedbackMixin, CreateView):
    form_class = EnrollmentForm
    template_name = "form.html"
    success_message = 'Matrícula em "{object.discipline}" registrada com sucesso.'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student.objects.select_related("course"), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Enrollment(student=self.student)
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs.setdefault("title", f"Matricular {self.student}")
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("aluno:student_detail", args=[self.student.pk])

    get_cancel_url = get_success_url


class EnrollmentStudentRedirectMixin:
    """Edição/exclusão de matrícula voltam pra página do aluno."""

    model = Enrollment

    def get_success_url(self):
        return reverse("aluno:student_detail", args=[self.object.student_id])

    get_cancel_url = get_success_url


class EnrollmentUpdateView(EnrollmentStudentRedirectMixin, HtmxModalUpdateMixin, UpdateView):
    fields = ["grade", "attendance"]
    template_name = "form.html"
    extra_context = {"title": "Lançar nota e frequência"}
    success_message = 'Nota de "{object.discipline}" salva com sucesso.'
    modal_form_template_name = "partials/modal_form.html"
    modal_success_template_name = "aluno/partials/enrollment_row.html"
    modal_object_name = "enrollment"
    modal_row_id_prefix = "enrollment-row"


class EnrollmentDeleteView(EnrollmentStudentRedirectMixin, HtmxModalDeleteMixin, DeleteView):
    template_name = "confirm_delete.html"
    extra_context = {"title": "Excluir matrícula"}
    success_message = 'Matrícula em "{object.discipline}" excluída.'
    modal_confirm_template_name = "partials/modal_confirm_delete.html"
    modal_row_id_prefix = "enrollment-row"