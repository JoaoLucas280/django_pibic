from django.db import models
from curso.models import Course

class Student(models.Model):
    name = models.CharField("Nome", max_length=100)
    email = models.EmailField("E-mail", unique=True)
    rgm = models.CharField("RGM", max_length=7, unique=True)
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
