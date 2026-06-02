from django.contrib import admin
from .models import Student, FeeRecord , Bus, Classroom

admin.site.register(Student)
admin.site.register(FeeRecord)
admin.site.register(Bus)
admin.site.register(Classroom)