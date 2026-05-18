from django import forms
from .models import Student, FeeRecord

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        
        fields = ['admission_no', 'name', 'student_class', 'parent', 'address', 'blood_group', 'bus_route', 'monthly_fee']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = ['month', 'amount_paid']
        widgets = {
            # This helps the user pick a date easily
            'month': forms.DateInput(attrs={'type': 'date'}),
        }