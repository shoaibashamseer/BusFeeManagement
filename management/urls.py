from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from management import views

urlpatterns = [
    # Login/Logout
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Logic URLs
    path('login-success/', views.login_success, name='login_success'),
    path('management/scanner/', views.scanner_page, name='scanner_page'),
    path('management/scan/<str:qr_id>/', views.scan_student, name='scan_student'),
    path('manual-lookup/', views.manual_lookup, name='manual_lookup'),
    path('management/dashboard/', views.manager_dashboard, name='manager_dashboard'),
]