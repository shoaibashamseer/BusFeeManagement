from django.contrib import admin
from .models import Qrcode_data, Student, FeeRecord , Bus

admin.site.register(Qrcode_data)
admin.site.register(Student)
admin.site.register(FeeRecord)
admin.site.register(Bus)
