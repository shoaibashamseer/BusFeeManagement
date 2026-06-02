from django.shortcuts import render, redirect, get_object_or_404
from .models import Student, FeeRecord , Bus , Classroom
from .forms import StudentForm, FeePaymentForm
from django.db.models import F, Sum, DecimalField
from django.db.models.functions import Coalesce
from datetime import date
import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from dateutil.relativedelta import relativedelta
from django.contrib import messages
import openpyxl
from django.http import JsonResponse
from collections import defaultdict
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
import uuid


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

@login_required
def scan_student(request, qr_id):
    # Lookup handles both: Scanning unique QR strings or typing an explicit Admission Number
    student = Student.objects.filter(qr_code=qr_id).first() or Student.objects.filter(admission_no=qr_id).first()

    prepared_outstanding_records = []
    total_past_delay = 0
    fees = []

    # Current School Year Window tracking specifically starting from June
    today = timezone.now().date()
    if today.month in [1, 2, 3]:
        academic_start_year = today.year - 1
    else:
        academic_start_year = today.year

    # Client constraint requirement: Shift timeline anchor precisely to June 1st
    session_start = datetime.date(academic_start_year, 5, 1)
    session_end = datetime.date(academic_start_year + 1, 3, 31)

    if student:
        # Fetch payment ledgers (ordered newest to oldest)
        fees = student.fees.all().order_by('-month')

        # Calculate outstanding balances from June
        db_outstanding_records = student.fees.filter(
            amount_paid__lt=student.monthly_fee,
            month__gte=session_start,
            month__lte=session_end
        ).order_by('month')

        for record in db_outstanding_records:
            balance_owed = int(student.monthly_fee - record.amount_paid)
            total_past_delay += balance_owed
            prepared_outstanding_records.append({
                'database_row': record,
                'month_name': record.month.strftime('%B %Y'),
                'remaining_balance': balance_owed
            })

    if request.method == 'POST':
        # CASH COLLECTION PROCESSOR ONLY (Profile details code completely deleted)
        if 'collect_cash' in request.POST and student:
            raw_amount = request.POST.get('amount_paid', '').strip()

            try:
                amount_received = int(raw_amount) if raw_amount else 0
            except ValueError:
                amount_received = 0

            if amount_received > 0:
                current_month_first_day = today.replace(day=1)

                record, created = student.fees.get_or_create(
                    month=current_month_first_day,
                    defaults={
                        'amount_paid': 0,
                        'collected_by': request.user,
                        'payment_date': today
                    }
                )

                record.amount_paid = int(record.amount_paid) + amount_received
                record.payment_date = today
                record.collected_by = request.user
                record.save()

                messages.success(request, f"₹{amount_received} successfully posted to ledger records!")
            else:
                messages.warning(request, "Collection rejected. Please enter a valid payment amount.")

            return redirect('scan_student', qr_id=qr_id)

    return render(request, 'management/student_detail.html', {
        'student': student,
        'fees': fees,
        'qr_id': qr_id,
        'outstanding_records': prepared_outstanding_records,
        'total_past_delay': total_past_delay,
    })


@login_required
def manager_dashboard(request):
    today = timezone.now().date()

    # Academic Window Alignment (June to March)
    if today.month in [1, 2, 3]:
        academic_start_year = today.year - 1
    else:
        academic_start_year = today.year

    # Synchronized timeline anchor shifted to June 1st
    session_start = datetime.date(academic_start_year, 6, 1)
    session_end = datetime.date(academic_start_year + 1, 3, 31)

    # Pre-calculate the first day of the current active month for status checking
    current_month_start = today.replace(day=1)

    # Prefetch 'fees' and select related 'bus' + 'collected_by' user details to speed up evaluation
    all_students = Student.objects.select_related('bus').prefetch_related('fees__collected_by').all()

    total_collection = 0
    total_delay = 0

    class_totals = defaultdict(lambda: {'collected': 0, 'delayed': 0})
    bus_totals = defaultdict(lambda: {'collected': 0, 'delayed': 0})
    grouped_data = defaultdict(lambda: defaultdict(list))

    for s in all_students:
        s_class = str(s.student_class).strip()

        if not s.bus:
            continue

        bus_key = f"Bus {s.bus.bus_number} — {s.bus.route_name}"
        base_fee = int(getattr(s, 'monthly_fee', 1000))

        # 1. Fetch total historical logs for the student from June to March
        student_session_records = s.fees.filter(
            month__gte=session_start,
            month__lte=session_end
        )

        student_paid = int(student_session_records.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0)

        # Calculate how many months have actually passed from June up to the current month
        # This keeps expected metrics accurate even if DB records don't exist yet
        if today >= session_start and today <= session_end:
            months_elapsed = (today.year - session_start.year) * 12 + today.month - session_start.month + 1
        elif today > session_end:
            months_elapsed = 10 # Total months in the academic block (June to March)
        else:
            months_elapsed = 1

        student_expected = months_elapsed * base_fee
        student_delay = max(0, student_expected - student_paid)

        # Assign properties to the student object for template rendering
        s.balance = student_delay

        # 2. FIX FOR STATUS & COLLECTED BY: Explicitly locate current month's entry
        current_month_record = student_session_records.filter(month=current_month_start).first()

        if current_month_record and current_month_record.amount_paid >= base_fee:
            s.paid_target_month = True
        else:
            s.paid_target_month = False

        # Add tracking property for who collected the latest payment in this session context
        latest_record = student_session_records.order_by('-payment_date', '-id').first()
        if latest_record and latest_record.collected_by:
            s.latest_collector = latest_record.collected_by.username
        else:
            s.latest_collector = None

        # Cumulative metric summaries
        total_collection += student_paid
        total_delay += student_delay

        class_totals[s_class]['collected'] += student_paid
        class_totals[s_class]['delayed'] += student_delay

        bus_totals[bus_key]['collected'] += student_paid
        bus_totals[bus_key]['delayed'] += student_delay

        grouped_data[s_class][bus_key].append(s)

    class_summary = []
    for c_name, data in class_totals.items():
        class_summary.append({
            'class_name': c_name,
            'total_collected': data['collected'],
            'total_delayed': data['delayed'],
        })

    bus_summary = []
    for b_label, data in bus_totals.items():
        bus_summary.append({
            'bus_label': b_label,
            'total_collected': data['collected'],
            'total_delay': data['delayed']
        })

    final_dashboard_data = {}
    for s_class, buses in sorted(grouped_data.items()):
        sorted_buses = sorted(
            buses.items(),
            key=lambda item: (item[0] == "No Bus Assigned", item[0])
        )
        final_dashboard_data[s_class] = sorted_buses

    return render(request, 'management/manager_dashboard.html', {
        'dashboard_data': final_dashboard_data,
        'billing_month_name': today.strftime('%B %Y'),
        'total_collection': total_collection,
        'total_delay': total_delay,
        'class_summary': sorted(class_summary, key=lambda x: x['class_name']),
        'bus_summary': sorted(bus_summary, key=lambda x: x['bus_label']),
    })

@login_required
def manual_lookup(request):
    adm_no = request.GET.get('admission_no')

    student = Student.objects.filter(admission_no=adm_no).first()

    if student:

        return redirect('scan_student', qr_id=student.qr_code)
    else:
        messages.error(request, "Student not found with that Admission Number.")
        return redirect('scanner_page')

@login_required
def upload_students_excel(request):
    if request.method == "POST" and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active


            headers = [str(cell.value).strip().lower() for cell in sheet[1]]


            field_mapping = {
                'admission_no': ['admission no', 'admission_no', 'adm no', 'admission number', 'id'],
                'name': ['name', 'student name', 'student_name'],
                'student_class': ['class', 'student class', 'student_class', 'grade'],
                'parent': ['parent', 'parent name', 'guardian', 'father name'],
                'address': ['address', 'location', 'residential address'],
                'blood_group': ['blood group', 'blood_group', 'bg'],
                'bus': ['bus number', 'bus_no', 'bus', 'bus_number'],
                'monthly_fee': ['monthly fee', 'fee', 'monthly_fee', 'fees']
            }


            col_indices = {}
            for field, aliases in field_mapping.items():
                found_index = None
                for alias in aliases:
                    if alias in headers:
                        found_index = headers.index(alias)
                        break
                col_indices[field] = found_index


            if col_indices['name'] is None or col_indices['student_class'] is None:
                messages.error(request, "Failed: Could not find 'Name' or 'Class' columns in the uploaded file.")
                return redirect('upload_students_excel')

            # 4. Process data rows safely using the discovered indexes
            success_count = 0
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):

                # Helper function to grab data safely even if the column doesn't exist in Excel
                def get_val(field_name, default=''):
                    idx = col_indices[field_name]
                    if idx is not None and idx < len(row) and row[idx] is not None:
                        return str(row[idx]).strip()
                    return default

                name = get_val('name')
                s_class = get_val('student_class')

                if not name or not s_class:  # Skip blank rows safely
                    continue


                adm_no = get_val('admission_no', default=f"TEMP-{row_idx}")
                parent = get_val('parent', default='Not Provided')
                address = get_val('address', default='Not Provided')
                bg = get_val('blood_group', default='')
                bus_num = get_val('bus', default=None)

                try:
                    fee = float(get_val('monthly_fee', default=0.00))
                except ValueError:
                    fee = 0.00


                bus_obj = None
                if bus_num:
                    bus_obj = Bus.objects.filter(bus_number=bus_num).first()


                Student.objects.update_or_create(
                    admission_no=adm_no,
                    defaults={
                        'name': name,
                        'student_class': s_class,
                        'parent': parent,
                        'address': address,
                        'blood_group': bg,
                        'bus': bus_obj,
                        'monthly_fee': fee
                    }
                )
                success_count += 1

            messages.success(request, f"Successfully processed {success_count} students from Excel!")
            return redirect('manager_dashboard')

        except Exception as e:
            messages.error(request, f"Error processing file: {e}")

    return render(request, 'management/upload_excel.html')

@login_required
def link_qr_scanner(request):
    # 1. Handle Card Assignment Request (POST)
    if request.method == "POST":
        student_id = request.POST.get('student_id') or request.POST.get('selectedStudentId')
        qr_code_value = request.POST.get('qr_code', '').strip()

        if student_id and qr_code_value:
            try:
                # Fetch the targeted student profile

                student = get_object_or_404(Student, id=student_id)

                # CRITICAL SELECTION: Check if ANY other student already claims this exact QR string
                existing_owner = Student.objects.filter(qr_code=qr_code_value).exclude(id=student.id).first()

                if existing_owner:
                    # BLOCK ASSIGNMENT: Raise a warning notice identifying the original owner
                    messages.error(
                        request,
                        f"Registration Denied: This QR card code is already linked to {existing_owner.name}."
                    )
                    return redirect('link_qr_scanner')

                # If the string is completely unique, update the record fields safely
                student.qr_code = qr_code_value
                student.save()

                messages.success(request, f"Successfully linked card token to {student.name}!")
                return redirect('link_qr_scanner')

            except Exception as e:
                messages.error(request, f"System Error: Could not verify assignment. {str(e)}")
                return redirect('link_qr_scanner')
        else:
            messages.error(request, "Invalid submission parameters. Please select a student card row.")
            return redirect('link_qr_scanner')

    # 2. Handle Directory Load (GET)

    students = Student.objects.all().order_by('student_class', 'name')
    return render(request, 'management/link_qr_scanner.html', {'students': students})

@login_required
def assign_card_to_student(request):
    if request.method == "POST":
        qr_id = request.POST.get('qr_id')
        student_id = request.POST.get('student_id')

        if not qr_id or not student_id:
            return JsonResponse({'status': 'error', 'message': 'Missing Card ID or Student ID.'})

        student = Student.objects.filter(id=student_id).first()

        if student:

            Student.objects.filter(qr_code=qr_id).update(qr_code=None)


            student.qr_code = qr_id
            student.save()

            return JsonResponse({'status': 'success', 'message': f"Card linked to {student.name}!"})

    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})


@login_required
def register_teacher(request):
    # Only allow the manager/superuser to create accounts
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Only managers can register staff.")
        return redirect('manager_dashboard')

    if request.method == "POST":
        username = request.POST.get('username','').strip()
        email = request.POST.get('email','').strip()
        password = request.POST.get('password')
        classroom_name = request.POST.get('classroom_name','').strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, "A teacher with this username already exists.")
            return redirect('register_teacher')

        # Create the staff credential
        new_teacher = User.objects.create_user(username=username, email=email, password=password)
        new_teacher.is_staff = True # Grants access to login systems
        new_teacher.save()

        if classroom_name:
            # Look up if class exists, or generate a fresh database row automatically
            classroom, created = Classroom.objects.get_or_create(
                name=classroom_name
            )

            # Link this classroom to our newly created teacher
            classroom.teacher = new_teacher
            classroom.save()

            msg_suffix = f" and assigned to Classroom: {classroom_name}."
        else:
            msg_suffix = " (without classroom assignment)."

        messages.success(request, f"Successfully created credentials for {username}{msg_suffix}")
        return redirect('teacher_reports')

    classrooms = Classroom.objects.filter(teacher__isnull=True)
    return render(request, 'management/register_teacher.html', {'classrooms': classrooms})


@login_required
def teacher_monthly_reports(request):
    if not request.user.is_superuser:
        return redirect('login')

    now = timezone.now()

    # Fetch all staff users
    teachers = User.objects.filter(is_staff=True, is_superuser=False)
    report_data = []

    for teacher in teachers:
        # Get their class name
        assigned_class = getattr(teacher, 'assigned_class', None)
        class_name = assigned_class.name if assigned_class else "No Class Assigned"

        # Calculate fees collected by this teacher THIS MONTH
        monthly_collection = teacher.collections.filter(
            updated_at__year=now.year,
            updated_at__month=now.month
        ).aggregate(total=Sum('amount_paid'))['total'] or 0.00

        report_data.append({
            'teacher_name': teacher.get_full_name() or teacher.username,
            'class_name': class_name,
            'collection_this_month': monthly_collection
        })

    return render(request, 'management/teacher_reports.html', {
        'reports': report_data,
        'current_month': now.strftime('%B %Y')
    })

@login_required
def pending_dues_report(request):
    # Fetch ONLY students with a bus assigned AND an active outstanding balance > 0
    pending_students = Student.objects.filter(
        bus__isnull=False
    ).annotate(
        # Follows relation to 'fees' record table and vertical-sums the values per student
        total_charged=Coalesce(Sum('monthly_fee'), 0, output_field=DecimalField()),
        total_paid=Coalesce(Sum('fees__amount_paid'), 0, output_field=DecimalField()),
    ).annotate(
        # Subtract the aggregated sums horizontally across the resulting object row
        pending_amount=F('total_charged') - F('total_paid')
    ).filter(
        pending_amount__gt=0
    ).order_by('student_class', 'name')

    # Calculate grand total overall outstanding deficit metric safely
    grand_total_pending = pending_students.aggregate(
        total=Sum('pending_amount')
    )['total'] or 0

    context = {
        'pending_students': pending_students,
        'grand_total_pending': grand_total_pending,
    }
    return render(request, 'management/pending_dues_report.html', context)

@login_required
def manager_create_student(request):

    buses = Bus.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        admission_no = request.POST.get('admission_no', '').strip()
        student_class = request.POST.get('student_class', '').strip()
        parent = request.POST.get('parent', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip() or None
        photo = request.POST.get('photo', '').strip() or None
        blood_group = request.POST.get('blood_group', '').strip()
        monthly_fee = request.POST.get('monthly_fee', '0.00')
        bus_id = request.POST.get('bus')
        qr_code = request.POST.get('qr_code', '').strip() or None

        # Validation 1: Guarantee Unique Admission Number
        if Student.objects.filter(admission_no=admission_no).exists():
            messages.error(request, f"❌ Registration failed: Admission No '{admission_no}' already exists in the system.")
            return render(request, 'management/add_student_form.html', {'buses': buses})

        # Validation 2: Guarantee Unique QR code if one was provided
        if qr_code and Student.objects.filter(qr_code=qr_code).exists():
            messages.error(request, f"❌ Registration failed: QR Code identity allocation sequence is already linked to another student.")
            return render(request, 'management/add_student_form.html', {'buses': buses})

        # Find matching bus if assigned
        assigned_bus = Bus.objects.filter(id=bus_id).first() if bus_id else None

        # Build database student entry
        try:
            Student.objects.create(
                name=name,
                admission_no=admission_no,
                student_class=student_class,
                parent=parent,
                address=address,
                phone=phone,
                photo=photo,
                blood_group=blood_group,
                monthly_fee=monthly_fee,
                bus=assigned_bus,
                qr_code=qr_code
            )
            messages.success(request, f"🎉 Student '{name}' onboarded into system registry successfully!")
            return redirect('add_new_student') # Reloads form clean on success
        except Exception as e:
            messages.error(request, f"❌ System processing error: {str(e)}")

    return render(request, 'management/add_student_form.html', {'buses': buses})