from django.shortcuts import render, redirect, get_object_or_404
from .models import Student, FeeRecord , Qrcode_data
from .forms import StudentForm, FeePaymentForm 
from django.db.models import Sum
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from dateutil.relativedelta import relativedelta
from django.contrib import messages

@login_required
def login_success(request):
    
    if request.user.is_superuser or request.user.groups.filter(name='Manager').exists():
        return redirect('manager_dashboard')
    else:
        return redirect('scanner_page')
    

def scanner_page(request):
    
    return render(request, 'management/scanner.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def scan_student(request, qr_id):
    # 1. Get or create the QR ID entry
    qr_entry, created = Qrcode_data.objects.get_or_create(qr_code_id=qr_id)
    
    # 2. Check if a student is already attached to this QR ID
    student = Student.objects.filter(qr_data=qr_entry).first()
    
    if request.method == 'POST':
        if student:
            
            form = StudentForm(request.POST, instance=student)
            fee_form = FeePaymentForm(request.POST) 
        else:
            
            form = StudentForm(request.POST)
            fee_form = None

        if form.is_valid():
            new_student = form.save(commit=False)
            new_student.qr_data = qr_entry
            new_student.save()
            return redirect('scan_student', qr_id=qr_id)
            
        
        if fee_form and fee_form.is_valid():
            payment = fee_form.save(commit=False)
            payment.student = student
            payment.collected_by = request.user
            payment.save()
            return redirect('scan_student', qr_id=qr_id)

    else:
        
        if student:
            form = StudentForm(instance=student) # Pre-fill with existing data
            fee_form = FeePaymentForm(initial={'amount_paid': student.monthly_fee})
            fees = student.fees.all().order_by('-month')
        else:
            form = StudentForm()
            fee_form = None
            fees = []

    return render(request, 'management/student_detail.html', {
        'form': form,
        'student': student,
        'fee_form': fee_form,
        'fees': fees,
        'qr_id': qr_id
    })

def manager_dashboard(request):
    
    students = Student.objects.select_related('bus', 'qr_data').order_by('bus__bus_number', 'student_class')
    today = date.today()
    target_month = today - relativedelta(months=1)
    total_collection = FeeRecord.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_delay = 0

    for s in students:
        start_date = s.created_at.date()
        
        # 1. Total money this student has ever paid
        actual_paid = s.fees.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

        # 2. Check if they joined THIS month (May)
        if start_date > target_month:
            # For a student joining this month, target_month (April) doesn't apply to them.
            # Instead, we check if they have paid for the CURRENT month (May).
            has_paid_this_month = s.fees.filter(
                month__year=today.year, 
                month__month=today.month
            ).exists()
            
            s.paid_target_month = has_paid_this_month
            
            if has_paid_this_month:
                s.balance = 0  # Paid up, clean slate
            else:
                s.balance = s.monthly_fee  # Haven't paid May fee yet!
                
        else:
            # 3. OLD STUDENTS LOGIC (Normal billing loop for past months)
            s.paid_target_month = s.fees.filter(
                month__year=target_month.year, 
                month__month=target_month.month
            ).exists()

            diff = relativedelta(target_month, start_date)
            months_to_bill = (diff.years * 12) + diff.months + 1
            
            expected_upto_target = months_to_bill * s.monthly_fee
            s.balance = expected_upto_target - actual_paid

        # 4. Add to the manager's total outstanding tracking
        total_delay += max(0, s.balance)
        

    return render(request, 'management/manager_dashboard.html', {
        'students': students,
        'billing_month_name': target_month.strftime('%B'),
        'total_collection': total_collection,
        'total_delay': total_delay,
    })

def manual_lookup(request):
    adm_no = request.GET.get('admission_no')
    # Assuming 'admission_no' is a field in your Student model
    student = Student.objects.filter(admission_no=adm_no).first()
    
    if student:
        # Redirect to the same scan page using their linked QR ID
        return redirect('scan_student', qr_id=student.qr_data.qr_code_id)
    else:
        messages.error(request, "Student not found with that Admission Number.")
        return redirect('scanner_page')