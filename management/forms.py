from django import forms
from .models import Student, FeeRecord, Bus

class StudentForm(forms.ModelForm):
    bus = forms.ModelChoiceField(
        queryset=Bus.objects.all(),
        empty_label="-- Select Bus Route --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Student

        fields = ['bus','admission_no', 'name', 'student_class', 'parent', 'address', 'blood_group', 'monthly_fee']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = ['month', 'amount_paid']
        widgets = {

            'month': forms.DateInput(attrs={'type': 'date'}),
        }