from django.contrib import admin
 
from .models import Course, Discipline, Semester
 
 
class SemesterInline(admin.TabularInline):
    model = Semester
    extra = 1
    fields = ("number", "disciplines")
    autocomplete_fields = ("disciplines",)
 
 
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_semesters")
    search_fields = ("name",)
    inlines = [SemesterInline]
 
 
@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "class_load")
    search_fields = ("name", "code")
 
 
@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("course", "number")
    list_filter = ("course",)
    search_fields = ("course__name",)
    filter_horizontal = ("disciplines",)