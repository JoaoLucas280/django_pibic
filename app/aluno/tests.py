from django.test import TestCase
from django.urls import reverse

from curso.models import Course

from .models import Student


class StudentModalTests(TestCase):
    def setUp(self):
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
