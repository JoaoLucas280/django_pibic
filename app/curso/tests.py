from django.test import TestCase
from django.urls import reverse

from .admin import SemesterInline
from .models import Course, Discipline, Semester


class SemesterEditingTests(TestCase):
    def setUp(self):
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
        self.assertContains(response, "htmx.org@2.0.4")

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
        self.assertEqual(
            set(self.semester.disciplines.values_list("pk", flat=True)),
            {discipline.pk for discipline in self.disciplines},
        )
        for discipline in self.disciplines:
            self.assertContains(response, discipline.name)

    def test_creating_semester_returns_to_course_list(self):
        response = self.client.post(
            reverse("curso:semester_create"),
            {
                "course": self.course.pk,
                "number": 2,
                "disciplines": [discipline.pk for discipline in self.disciplines],
            },
        )

        self.assertRedirects(response, reverse("curso:course_list"))
        self.assertTrue(
            Semester.objects.filter(course=self.course, number=2).exists()
        )

    def test_course_semester_inline_allows_multiple_disciplines(self):
        self.assertIn("disciplines", SemesterInline.fields)
        self.assertIn("disciplines", SemesterInline.autocomplete_fields)


class CourseAndDisciplineModalTests(TestCase):
    def setUp(self):
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
