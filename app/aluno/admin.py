from django.contrib import admin
 
from .models import Student
 
 
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "rgm", "email", "course")
    search_fields = ("name", "rgm", "email")
    list_filter = ("course",)
    autocomplete_fields = ("course",)
