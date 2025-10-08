from django.urls import path
from . import views
from .views import fingerprint_data_view, admin_dashboard_view
from .views import get_today_dashboard_data
from .views import send_attendance_report_via_email
from django.urls import path
from .views import active_meeting_api, start_meeting, end_meeting




urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('request_leave/', views.request_leave_view, name='leave_requests'),
    path('start_break/', views.start_break_view, name='start_break'),
    path('end_break/', views.end_break_view, name='end_break'),
    path('fingerprint_data/', fingerprint_data_view, name='fingerprint_data'),
    path('admin-dashboard/', admin_dashboard_view, name='admin-dashboard'),
    path('generate_report/', views.generate_attendance_report, name='generate_report'),
    path('leave_history/', views.leave_history_view, name='leave_history'),
    path('attendance_history/', views.attendance_history_view, name='attendance_history'),
    path('leave/request/', views.request_leave_view, name='request_leave'),
    path("api/dashboard-data/", get_today_dashboard_data, name="dashboard-data"),
    path('generate-report/', views.generate_attendance_report, name='generate_attendance_report'),
    path('view-monthly-report/', views.view_monthly_report, name='view_monthly_report'),
    path('generate-pdf/', views.generate_attendance_pdf, name='generate_attendance_pdf'),
    path('send_report_email/', send_attendance_report_via_email, name='send_report_email'),
    path("quick-view-dashboard/", views.quick_view_dashboard, name="quick_view_dashboard"),
    path("employee-home/", views.employee_home, name="employee_home"),
    path('api/active_meeting/', active_meeting_api, name='active_meeting_api'),
    path('start_meeting/', views.start_meeting, name='start_meeting'),
    path('end_meeting/', views.end_meeting, name='end_meeting'),
    path("api/leave/unseen-count/", views.unseen_leave_count_api, name="unseen_leave_count_api"),
    path("api/leave/reset-unseen/", views.reset_unseen_leave_api, name="reset_unseen_leave_api"),
    path("remote_checkin/", views.remote_checkin, name="remote_checkin"),
    path("remote_checkout/", views.remote_checkout, name="remote_checkout"),

]

