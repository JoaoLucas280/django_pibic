from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from curso.models import Course, Discipline

# Regras de aprovação. Frequência mínima de 75% é exigência da LDB (Lei 9.394/96, art. 24).
# ponytail: média fixa no código; vira configuração se o sistema atender instituições com regras diferentes
APPROVAL_GRADE = Decimal("6.0")
MIN_ATTENDANCE = 75

class Student(models.Model):
    name = models.CharField("Nome", max_length=100)
    email = models.EmailField("E-mail", unique=True)
    rgm = models.CharField(
        "RGM",
        max_length=7,
        unique=True,
        validators=[RegexValidator(r"^\d{7}$", "O RGM deve ter exatamente 7 dígitos numéricos.")],
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="Curso",
    )
 
    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ["name"]
 
    def __str__(self):
        return self.name


class Enrollment(models.Model):
    """Matrícula de um aluno numa disciplina, com nota e frequência."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="enrollments", verbose_name="Aluno"
    )
    discipline = models.ForeignKey(
        # PROTECT: disciplina com notas lançadas não some do histórico
        Discipline, on_delete=models.PROTECT, related_name="enrollments", verbose_name="Disciplina"
    )
    grade = models.DecimalField(
        "Nota", max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="De 0 a 10. Deixe em branco enquanto não houver nota.",
    )
    attendance = models.PositiveSmallIntegerField(
        "Frequência (%)", null=True, blank=True,
        validators=[MaxValueValidator(100)],
        help_text="De 0 a 100. Deixe em branco enquanto não houver frequência.",
    )

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        ordering = ["discipline__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "discipline"],
                name="unique_enrollment_per_student",
                violation_error_message="Este aluno já está matriculado nessa disciplina.",
            ),
        ]

    def clean(self):
        # Só disciplinas da grade do curso do aluno
        if self.student_id and self.discipline_id:
            in_curriculum = Discipline.objects.filter(
                pk=self.discipline_id, semesters__course_id=self.student.course_id
            ).exists()
            if not in_curriculum:
                raise ValidationError({
                    "discipline": f"Essa disciplina não faz parte da grade de {self.student.course}."
                })

    @property
    def status(self):
        if self.grade is None or self.attendance is None:
            return "Cursando"
        if self.attendance < MIN_ATTENDANCE:
            return "Reprovado por falta"
        if self.grade < APPROVAL_GRADE:
            return "Reprovado"
        return "Aprovado"

    def __str__(self):
        return f"{self.student} em {self.discipline}"
