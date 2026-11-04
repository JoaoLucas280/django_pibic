from django.contrib import admin
 
from .models import Enrollment, Student


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    fields = ("discipline", "grade", "attendance")
    autocomplete_fields = ("discipline",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "rgm", "email", "course")
    search_fields = ("name", "rgm", "email")
    list_filter = ("course",)
    autocomplete_fields = ("course",)
    inlines = [EnrollmentInline]
