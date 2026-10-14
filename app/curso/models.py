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
 
    def __str__(self):
        return f"{self.course.name} - {self.number}º semestre"
