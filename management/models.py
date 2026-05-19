
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Qrcode_data(models.Model):
    qr_code_id = models.CharField(max_length=100, unique=True)
    is_assigned = models.BooleanField(default=False)

    def __str__(self):
        return self.qr_code_id
    
class Bus(models.Model):
    bus_number = models.CharField(max_length=20, unique=True)
    route_name = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=15)
    aaya_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Bus {self.bus_number} - {self.route_name}"
    
class Student(models.Model):
    qr_data = models.OneToOneField(Qrcode_data, on_delete=models.CASCADE)
    bus_route = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, related_name='students')
    admission_no =  models.CharField(max_length=200 , null=True , blank=True)
    name = models.CharField(max_length=200)
    student_class = models.CharField(max_length=50)
    parent = models.CharField(max_length=200)
    address = models.TextField()
    blood_group = models.CharField(max_length=5)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.qr_data}"

class FeeRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees')
    collected_by = models.ForeignKey(User, on_delete=models.PROTECT,null=True , blank= True)
    month = models.DateField() # Store the first day of the month paid for
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('student', 'month') 



    