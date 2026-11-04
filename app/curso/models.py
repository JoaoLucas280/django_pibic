from django.core.exceptions import ValidationError
from django.db import models
 
 
class Course(models.Model):
    name = models.CharField("Nome", max_length=100, unique=True)
    duration_semesters = models.PositiveIntegerField("Duração (semestres)")
 
    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["name"]
 
    def __str__(self):
        return self.name
 
 
class Discipline(models.Model):
    name = models.CharField("Nome", max_length=100)
    code = models.CharField("Código", max_length=20, blank=True)
    class_load = models.PositiveIntegerField("Carga horária (horas)")
 
    class Meta:
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"
        ordering = ["name"]
 
    def __str__(self):
        return self.name
 
 
class Semester(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="semesters",
        verbose_name="Curso",
    )
    number = models.PositiveIntegerField("Número do semestre")
    disciplines = models.ManyToManyField(
        Discipline,
        related_name="semesters",
        blank=True,
        verbose_name="Disciplinas",
    )
 
    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        ordering = ["course", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "number"],
                name="unique_semester_per_course",
                violation_error_message="Este curso já possui um semestre com esse número.",
            ),
        ]

    def clean(self):
        if self.number is not None and self.number < 1:
            raise ValidationError({"number": "O número do semestre deve ser 1 ou maior."})
        if self.course_id and self.number and self.number > self.course.duration_semesters:
            raise ValidationError({
                "number": f"O curso {self.course} tem só {self.course.duration_semesters} semestres."
            })

    def __str__(self):
        return f"{self.course.name} - {self.number}º semestre"
