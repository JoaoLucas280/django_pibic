from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from curso.models import Course

from .models import Student


class StudentModalTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Engenharia", duration_semesters=8)
        self.student = Student.objects.create(
            name="Ana Silva",
            rgm="1234567",
            email="ana@example.com",
            course=self.course,
        )

    def test_student_list_has_modal_actions(self):
        response = self.client.get(reverse("aluno:student_list"))

        self.assertContains(response, 'id="action-modal"')
        self.assertContains(response, 'data-modal-title="Editar aluno"')
        self.assertContains(response, 'data-modal-title="Excluir aluno"')

    def test_student_edit_modal_saves_and_refreshes_the_row(self):
        response = self.client.post(
            reverse("aluno:student_update", args=[self.student.pk]),
            {
                "name": "Ana Souza",
                "rgm": "1234567",
                "email": "ana@example.com",
                "course": self.course.pk,
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["HX-Retarget"],
            f"#student-row-{self.student.pk}",
        )
        self.assertContains(response, "Ana Souza")
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "Ana Souza")

    def test_student_delete_modal_confirms_and_removes_the_row(self):
        response = self.client.get(
            reverse("aluno:student_delete", args=[self.student.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, 'hx-post="')
        self.assertContains(response, "Excluir")
        self.assertNotContains(response, "<!DOCTYPE html>")

        response = self.client.post(
            reverse("aluno:student_delete", args=[self.student.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["HX-Retarget"],
            f"#student-row-{self.student.pk}",
        )
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())


class StudentRgmValidationTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Direito", duration_semesters=10)
        self.url = reverse("aluno:student_create")

    def post(self, rgm):
        return self.client.post(self.url, {
            "name": "Bia", "email": f"bia{rgm}@x.com", "rgm": rgm, "course": self.course.pk,
        })

    def test_invalid_rgms_are_rejected(self):
        for rgm in ["D080004", "114.008", "123456", "abcdefg"]:
            with self.subTest(rgm=rgm):
                response = self.post(rgm)
                self.assertContains(response, "exatamente 7 dígitos")
        self.assertFalse(Student.objects.exists())

    def test_valid_rgm_is_accepted(self):
        self.post("0123456")
        self.assertTrue(Student.objects.filter(rgm="0123456").exists())

class EnrollmentTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from curso.models import Discipline, Semester
        from .models import Enrollment
        self.Decimal, self.Enrollment = Decimal, Enrollment
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Engenharia", duration_semesters=8)
        self.calc = Discipline.objects.create(name="Cálculo", code="MAT1", class_load=60)
        self.fisica = Discipline.objects.create(name="Física", code="FIS1", class_load=60)
        self.direito = Discipline.objects.create(name="Direito Civil", code="DIR1", class_load=60)
        Semester.objects.create(course=self.course, number=1).disciplines.add(self.calc, self.fisica)
        self.student = Student.objects.create(name="Lara", email="lara@x.com", rgm="5556667", course=self.course)

    def enroll(self, discipline, grade=None, attendance=None):
        return self.Enrollment.objects.create(student=self.student, discipline=discipline, grade=grade, attendance=attendance)

    def test_status_rules(self):
        D = self.Decimal
        cases = [
            (None, None, "Cursando"),
            (D("8"), None, "Cursando"),
            (D("6.0"), 75, "Aprovado"),          # exatamente no limite: aprova
            (D("5.9"), 100, "Reprovado"),
            (D("10"), 74, "Reprovado por falta"),  # falta reprova mesmo com nota máxima
        ]
        for grade, attendance, expected in cases:
            with self.subTest(grade=grade, attendance=attendance):
                self.assertEqual(self.Enrollment(grade=grade, attendance=attendance).status, expected)

    def test_form_offers_only_curriculum_disciplines_not_yet_taken(self):
        self.enroll(self.calc)
        response = self.client.get(reverse("aluno:enrollment_create", args=[self.student.pk]))
        offered = list(response.context["form"].fields["discipline"].queryset)
        self.assertEqual(offered, [self.fisica])  # sem Cálculo (já cursa) e sem Direito (outro curso)

    def test_enrolling_in_other_course_discipline_is_rejected(self):
        response = self.client.post(
            reverse("aluno:enrollment_create", args=[self.student.pk]), {"discipline": self.direito.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.Enrollment.objects.exists())

    def test_enroll_redirects_to_student_with_message(self):
        response = self.client.post(
            reverse("aluno:enrollment_create", args=[self.student.pk]), {"discipline": self.fisica.pk}, follow=True
        )
        self.assertRedirects(response, reverse("aluno:student_detail", args=[self.student.pk]))
        self.assertContains(response, "Matrícula em &quot;Física&quot; registrada com sucesso.")

    def test_htmx_grade_update_returns_row_with_new_status(self):
        enrollment = self.enroll(self.calc)
        response = self.client.post(
            reverse("aluno:enrollment_update", args=[enrollment.pk]),
            {"grade": "7.5", "attendance": "90"}, HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response["HX-Retarget"], f"#enrollment-row-{enrollment.pk}")
        self.assertContains(response, "Aprovado")
        self.assertContains(response, "7,5")

    def test_grade_out_of_range_is_rejected(self):
        enrollment = self.enroll(self.calc)
        response = self.client.post(
            reverse("aluno:enrollment_update", args=[enrollment.pk]), {"grade": "11", "attendance": "101"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].errors), 2)

    def test_report_card_average_and_approvals(self):
        D = self.Decimal
        self.enroll(self.calc, D("8"), 90)
        self.enroll(self.fisica, D("5"), 90)
        response = self.client.get(reverse("aluno:student_detail", args=[self.student.pk]))
        self.assertEqual(response.context["average"], D("6.5"))
        self.assertEqual(response.context["approved"], 1)

    def test_discipline_with_grades_cannot_be_deleted(self):
        self.enroll(self.calc, self.Decimal("8"), 90)
        response = self.client.post(reverse("curso:discipline_delete", args=[self.calc.pk]))
        self.assertContains(response, "Não é possível excluir")

class ReportCardTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from curso.models import Discipline, Semester
        from .models import Enrollment
        self.client.force_login(User.objects.create_user("secretaria"))
        course = Course.objects.create(name="Farmácia", duration_semesters=8)
        quimica = Discipline.objects.create(name="Química Geral", code="QUI1", class_load=80)
        Semester.objects.create(course=course, number=1).disciplines.add(quimica)
        self.student = Student.objects.create(name="Téo", email="teo@x.com", rgm="9998887", course=course)
        Enrollment.objects.create(student=self.student, discipline=quimica, grade=Decimal("9.5"), attendance=96)

    def test_report_card_is_a_print_ready_standalone_page(self):
        response = self.client.get(reverse("aluno:report_card", args=[self.student.pk]))
        self.assertContains(response, "<title>Boletim - Téo - RGM 9998887</title>", html=False)
        for text in ["Química Geral", "9,5", "96%", "Aprovado", "Farmácia", "@page", "window.print()"]:
            self.assertContains(response, text)
        self.assertNotContains(response, 'class="navbar')  # sem menu do sistema no documento

    def test_student_page_links_to_report_card(self):
        response = self.client.get(reverse("aluno:student_detail", args=[self.student.pk]))
        self.assertContains(response, reverse("aluno:report_card", args=[self.student.pk]))

    def test_report_card_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("aluno:report_card", args=[self.student.pk]))
        self.assertEqual(response.status_code, 302)

class PublicReportCardTests(TestCase):
    def setUp(self):
        from .views import REPORT_CARD_SALT
        from django.core import signing
        self.signing, self.salt = signing, REPORT_CARD_SALT
        self.client.force_login(User.objects.create_user("secretaria"))
        course = Course.objects.create(name="Odontologia", duration_semesters=10)
        self.student = Student.objects.create(name="Iara", email="iara@privado.com", rgm="2223334", course=course)

    def public_url(self):
        response = self.client.get(reverse("aluno:report_card", args=[self.student.pk]))
        return response.context["public_url"]

    def test_report_card_and_student_page_show_qr_code(self):
        for name in ["aluno:report_card", "aluno:student_detail"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=[self.student.pk]))
                self.assertContains(response, "<svg")
                self.assertTrue(response.context["public_url"].startswith("http://testserver/boletim/"))
        # Na página do aluno o QR também é um link clicável
        response = self.client.get(reverse("aluno:student_detail", args=[self.student.pk]))
        self.assertContains(response, f'href="{response.context["public_url"]}"')

    def test_qr_link_opens_without_login_and_hides_email(self):
        url = self.public_url()
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iara")
        self.assertContains(response, "Documento autêntico")
        self.assertNotContains(response, "iara@privado.com")

    def test_tampered_or_guessed_token_is_404(self):
        good = self.public_url().rstrip("/").rsplit("/", 1)[1]
        self.client.logout()
        forged = self.signing.dumps(self.student.pk, salt="outro-salt")  # assinado com salt errado
        for token in [good[:-1] + ("A" if good[-1] != "A" else "B"), str(self.student.pk), forged]:
            with self.subTest(token=token):
                self.assertEqual(self.client.get(f"/boletim/{token}/").status_code, 404)

    def test_other_pages_still_require_login(self):
        self.client.logout()
        response = self.client.get(reverse("aluno:student_detail", args=[self.student.pk]))
        self.assertEqual(response.status_code, 302)

class QrHostTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        course = Course.objects.create(name="Biologia", duration_semesters=8)
        self.student = Student.objects.create(name="Nina", email="nina@x.com", rgm="4445556", course=course)
        self.url = reverse("aluno:student_detail", args=[self.student.pk])

    def public_url(self, host):
        from unittest import mock
        with mock.patch("aluno.views.lan_ip", return_value="192.168.0.50"):
            return self.client.get(self.url, HTTP_HOST=host).context["public_url"]

    def test_localhost_access_uses_lan_ip_in_qr(self):
        for host in ["127.0.0.1:8000", "localhost:8000", "127.0.0.1"]:
            with self.subTest(host=host):
                port = ":8000" if ":" in host else ""
                self.assertTrue(self.public_url(host).startswith(f"http://192.168.0.50{port}/boletim/"))

    def test_lan_access_keeps_its_own_address(self):
        self.assertTrue(self.public_url("192.168.30.78:8000").startswith("http://192.168.30.78:8000/boletim/"))

    def test_qr_svg_scales_instead_of_being_cropped(self):
        # Regressão: SVG com width/height fixos e sem viewBox era cortado pelo CSS e ficava ilegível
        from .views import qr_svg
        svg = qr_svg("http://192.168.0.50:8000/boletim/x/")
        self.assertIn("viewBox", svg)
        self.assertNotRegex(svg.split(">", 1)[0], r'\swidth="')

    def test_qr_link_built_from_lan_ip_actually_opens(self):
        url = self.public_url("127.0.0.1:8000")
        self.client.logout()
        path = url.split("8000", 1)[1]
        self.assertEqual(self.client.get(path).status_code, 200)