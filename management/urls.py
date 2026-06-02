
from django.urls import path
from django.contrib.auth import views as auth_views
from management import views

urlpatterns = [

    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login-success/', views.login_success, name='login_success'),

    path('management/scanner/', views.scanner_page, name='scanner_page'),
    path('management/scan/<str:qr_id>/', views.scan_student, name='scan_student'),
    path('manual-lookup/', views.manual_lookup, name='manual_lookup'),

    path('management/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('upload-excel/', views.upload_students_excel, name='upload_students_excel'),
    path('link-qr/', views.link_qr_scanner, name='link_qr_scanner'),
    path('assign-card/', views.assign_card_to_student, name='assign_card_to_student'),
    path('manager/teachers/register/', views.register_teacher, name='register_teacher'),
    path('manager/reports/teachers/', views.teacher_monthly_reports, name='teacher_reports'),
    path('management/reports/dues/', views.pending_dues_report, name='pending_dues_report'),
    path('management/add-student/', views.manager_create_student, name='add_new_student'),
]
