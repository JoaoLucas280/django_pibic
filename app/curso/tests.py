import json
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .admin import SemesterInline
from .models import Course, Discipline, Semester


class SemesterEditingTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Engenharia", duration_semesters=8)
        self.semester = Semester.objects.create(course=self.course, number=1)
        self.disciplines = [
            Discipline.objects.create(
                name=f"Disciplina {number}",
                code=f"D{number}",
                class_load=60,
            )
            for number in range(1, 3)
        ]

    def test_course_page_offers_semester_edit_modal(self):
        response = self.client.get(reverse("curso:course_detail", args=[self.course.pk]))

        self.assertContains(response, 'id="semester-edit-modal"')
        self.assertContains(response, "hx-get=")
        self.assertContains(response, "vendor/htmx.min.js")

    def test_semester_modal_loads_a_multi_select_form(self):
        response = self.client.get(
            reverse("curso:semester_update", args=[self.semester.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, 'hx-post="')
        self.assertContains(response, 'type="checkbox"')
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_semester_modal_saves_multiple_disciplines(self):
        response = self.client.post(
            reverse("curso:semester_update", args=[self.semester.pk]),
            {
                "course": self.course.pk,
                "number": self.semester.number,
                "disciplines": [discipline.pk for discipline in self.disciplines],
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Retarget"], f"#semester-card-{self.semester.pk}")
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        self.assertIn("semesterUpdated", json.loads(response["HX-Trigger-After-Swap"]))
        self.assertEqual(
            set(self.semester.disciplines.values_list("pk", flat=True)),
            {discipline.pk for discipline in self.disciplines},
        )
        for discipline in self.disciplines:
            self.assertContains(response, discipline.name)

    def test_creating_semester_returns_to_course_detail(self):
        response = self.client.post(
            reverse("curso:semester_create"),
            {
                "course": self.course.pk,
                "number": 2,
                "disciplines": [discipline.pk for discipline in self.disciplines],
            },
        )

        self.assertRedirects(response, reverse("curso:course_detail", args=[self.course.pk]))
        self.assertTrue(
            Semester.objects.filter(course=self.course, number=2).exists()
        )

    def test_course_semester_inline_allows_multiple_disciplines(self):
        self.assertIn("disciplines", SemesterInline.fields)
        self.assertIn("disciplines", SemesterInline.autocomplete_fields)


class CourseAndDisciplineModalTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Engenharia", duration_semesters=8)
        self.semester = Semester.objects.create(course=self.course, number=1)
        self.discipline = Discipline.objects.create(
            name="Cálculo",
            code="MAT1",
            class_load=60,
        )

    def test_course_list_has_modal_actions(self):
        response = self.client.get(reverse("curso:course_list"))

        self.assertContains(response, 'id="action-modal"')
        self.assertContains(response, 'data-modal-title="Editar curso"')
        self.assertContains(response, 'data-modal-title="Excluir curso"')

    def test_course_edit_modal_saves_and_refreshes_the_row(self):
        response = self.client.post(
            reverse("curso:course_update", args=[self.course.pk]),
            {"name": "Engenharia Civil", "duration_semesters": 10},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Retarget"], f"#course-row-{self.course.pk}")
        self.assertContains(response, "Engenharia Civil")
        self.course.refresh_from_db()
        self.assertEqual(self.course.name, "Engenharia Civil")

    def test_course_delete_modal_confirms_and_removes_the_row(self):
        response = self.client.get(
            reverse("curso:course_delete", args=[self.course.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, 'hx-post="')
        self.assertContains(response, "Excluir")
        self.assertNotContains(response, "<!DOCTYPE html>")

        response = self.client.post(
            reverse("curso:course_delete", args=[self.course.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Retarget"], f"#course-row-{self.course.pk}")
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

    def test_discipline_edit_modal_saves_and_refreshes_the_row(self):
        response = self.client.post(
            reverse("curso:discipline_update", args=[self.discipline.pk]),
            {"name": "Cálculo I", "code": "MAT1", "class_load": 72},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["HX-Retarget"],
            f"#discipline-row-{self.discipline.pk}",
        )
        self.assertContains(response, "Cálculo I")
        self.discipline.refresh_from_db()
        self.assertEqual(self.discipline.class_load, 72)

    def test_discipline_delete_modal_confirms_and_removes_the_row(self):
        response = self.client.get(
            reverse("curso:discipline_delete", args=[self.discipline.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, 'hx-post="')
        self.assertContains(response, "Excluir")

        response = self.client.post(
            reverse("curso:discipline_delete", args=[self.discipline.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["HX-Retarget"],
            f"#discipline-row-{self.discipline.pk}",
        )
        self.assertFalse(Discipline.objects.filter(pk=self.discipline.pk).exists())


class ProtectedCourseDeleteTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        from aluno.models import Student
        self.course = Course.objects.create(name="Direito", duration_semesters=10)
        Student.objects.create(name="Ana", email="ana@x.com", rgm="1234567", course=self.course)
        self.url = reverse("curso:course_delete", args=[self.course.pk])

    def test_delete_course_with_students_shows_message(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não é possível excluir")
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_htmx_delete_course_with_students_shows_message(self):
        response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não é possível excluir")
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

class SemesterValidationTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Curso Curto", duration_semesters=4)
        Semester.objects.create(course=self.course, number=1)
        self.url = reverse("curso:semester_create")

    def post(self, number):
        return self.client.post(self.url, {"course": self.course.pk, "number": number})

    def test_duplicate_semester_is_rejected(self):
        response = self.post(1)
        self.assertContains(response, "já possui um semestre com esse número")
        self.assertEqual(Semester.objects.filter(course=self.course).count(), 1)

    def test_semester_beyond_duration_is_rejected(self):
        response = self.post(5)
        self.assertContains(response, "tem só 4 semestres")
        self.assertEqual(Semester.objects.filter(course=self.course).count(), 1)

    def test_semester_zero_is_rejected(self):
        response = self.post(0)
        self.assertContains(response, "deve ser 1 ou maior")

    def test_valid_semester_is_created(self):
        self.post(2)
        self.assertTrue(Semester.objects.filter(course=self.course, number=2).exists())

class LoginRequiredTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        for url in ["/cursos/", "/cursos/disciplinas/", "/alunos/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"/admin/login/?next={url}", fetch_redirect_response=False)

    def test_logged_user_can_access(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.assertEqual(self.client.get("/cursos/").status_code, 200)

class SemesterCreateFromCourseTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Pedagogia", duration_semesters=8)

    def test_course_is_prefilled_from_query_string(self):
        response = self.client.get(reverse("curso:semester_create") + f"?course={self.course.pk}")
        self.assertEqual(response.context["form"].initial["course"], str(self.course.pk))

    def test_redirects_back_to_course_after_create(self):
        response = self.client.post(reverse("curso:semester_create"), {"course": self.course.pk, "number": 1})
        self.assertRedirects(response, reverse("curso:course_detail", args=[self.course.pk]))

    def test_offline_assets_are_local(self):
        response = self.client.get(reverse("curso:course_list"))
        self.assertContains(response, "/static/vendor/htmx.min.js")
        self.assertNotContains(response, "unpkg.com")
        self.assertNotContains(response, "cdn.jsdelivr.net")

class DashboardTests(TestCase):
    def setUp(self):
        from aluno.models import Student
        self.client.force_login(User.objects.create_user("secretaria"))
        course = Course.objects.create(name="Psicologia", duration_semesters=10)
        Semester.objects.create(course=course, number=1)
        Discipline.objects.create(name="Ética", class_load=40)
        Student.objects.create(name="Caio", email="caio@x.com", rgm="7654321", course=course)

    def test_home_shows_totals_and_top_courses(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([total for _, total, _ in response.context["stats"]], [1, 1, 1, 1])
        self.assertContains(response, "Psicologia")
        self.assertContains(response, "1 de 10")

    def test_home_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get("/"), "/admin/login/?next=/", fetch_redirect_response=False)

class SuccessMessageTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Nutrição", duration_semesters=8)

    def test_create_shows_message_after_redirect(self):
        response = self.client.post(
            reverse("curso:course_create"), {"name": "Biomedicina", "duration_semesters": 8}, follow=True
        )
        self.assertContains(response, 'Curso &quot;Biomedicina&quot; cadastrado com sucesso.')

    def test_htmx_update_sends_message_in_header(self):
        response = self.client.post(
            reverse("curso:course_update", args=[self.course.pk]),
            {"name": "Nutrição Clínica", "duration_semesters": 8},
            HTTP_HX_REQUEST="true",
        )
        events = json.loads(response["HX-Trigger-After-Swap"])
        self.assertEqual(events["showMessage"], 'Curso "Nutrição Clínica" atualizado com sucesso.')
        self.assertIn("actionModalDone", events)
        response["HX-Trigger-After-Swap"].encode("ascii")  # acentos escapados: cabeçalho seguro

    def test_htmx_delete_sends_message_with_old_name(self):
        response = self.client.post(
            reverse("curso:course_delete", args=[self.course.pk]), HTTP_HX_REQUEST="true"
        )
        events = json.loads(response["HX-Trigger-After-Swap"])
        self.assertEqual(events["showMessage"], 'Curso "Nutrição" excluído com sucesso.')

    def test_blocked_delete_shows_no_success_message(self):
        from aluno.models import Student
        Student.objects.create(name="Lia", email="lia@x.com", rgm="1112223", course=self.course)
        response = self.client.post(reverse("curso:course_delete", args=[self.course.pk]), follow=True)
        self.assertNotContains(response, "excluído com sucesso")
        self.assertContains(response, "Não é possível excluir")

class CancelButtonTests(TestCase):
    def setUp(self):
        from aluno.models import Student
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Medicina", duration_semesters=12)
        self.discipline = Discipline.objects.create(name="Anatomia", class_load=80)
        self.semester = Semester.objects.create(course=self.course, number=1)
        self.student = Student.objects.create(name="Rui", email="rui@x.com", rgm="3334445", course=self.course)

    def cancel_href(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertNotContains(response, "history.back")
        return response.context["cancel_url"]

    def test_every_form_page_has_a_fixed_cancel_link(self):
        c, d, s, a = self.course.pk, self.discipline.pk, self.semester.pk, self.student.pk
        expected = {
            reverse("curso:course_create"): "/cursos/",
            reverse("curso:course_update", args=[c]): "/cursos/",
            reverse("curso:course_delete", args=[c]): "/cursos/",
            reverse("curso:discipline_create"): "/cursos/disciplinas/",
            reverse("curso:discipline_update", args=[d]): "/cursos/disciplinas/",
            reverse("curso:discipline_delete", args=[d]): "/cursos/disciplinas/",
            reverse("curso:semester_create"): "/cursos/",
            reverse("curso:semester_update", args=[s]): f"/cursos/{c}/",
            reverse("curso:semester_delete", args=[s]): f"/cursos/{c}/",
            reverse("aluno:student_create"): "/alunos/",
            reverse("aluno:student_update", args=[a]): "/alunos/",
            reverse("aluno:student_delete", args=[a]): "/alunos/",
        }
        for url, cancel in expected.items():
            with self.subTest(url=url):
                self.assertEqual(self.cancel_href(url), cancel)

    def test_new_semester_from_course_cancels_back_to_course(self):
        url = reverse("curso:semester_create")
        self.assertEqual(self.cancel_href(f"{url}?course={self.course.pk}"), f"/cursos/{self.course.pk}/")

    def test_invalid_course_param_falls_back_to_course_list(self):
        url = reverse("curso:semester_create")
        for bad in ["abc", "999999", "<script>"]:
            with self.subTest(bad=bad):
                self.assertEqual(self.cancel_href(f"{url}?course={bad}"), "/cursos/")

class SemestersInsideCourseTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretaria"))
        self.course = Course.objects.create(name="Arquitetura", duration_semesters=10)
        self.semester = Semester.objects.create(course=self.course, number=1)

    def test_semester_list_page_and_menu_item_are_gone(self):
        self.assertEqual(self.client.get("/cursos/semestres/").status_code, 404)
        self.assertNotContains(self.client.get("/cursos/"), ">Semestres</a>")

    def test_course_page_offers_semester_delete(self):
        response = self.client.get(reverse("curso:course_detail", args=[self.course.pk]))
        self.assertContains(response, reverse("curso:semester_delete", args=[self.semester.pk]))

    def test_htmx_delete_removes_card_from_course_page(self):
        response = self.client.post(
            reverse("curso:semester_delete", args=[self.semester.pk]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response["HX-Retarget"], f"#semester-card-{self.semester.pk}")
        self.assertIn("showMessage", json.loads(response["HX-Trigger-After-Swap"]))
        self.assertFalse(Semester.objects.filter(pk=self.semester.pk).exists())

    def test_full_page_delete_returns_to_course(self):
        response = self.client.post(reverse("curso:semester_delete", args=[self.semester.pk]))
        self.assertRedirects(response, reverse("curso:course_detail", args=[self.course.pk]))