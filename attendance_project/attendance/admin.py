from django.contrib import admin
from .models import Employee, Attendance, Leave, Break
# Registering models
admin.site.register(Employee)
# admin.site.register(Leave)
from django.core.exceptions import ValidationError
from django.db.models import F
from django.contrib import admin
from .models import Attendance, Employee
from django.db.models import F
from .models import LeaveBalance  # make sure this is imported
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from .models import Leave, LeaveBalance, Employee


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'date',
        'status',
        'check_in',
        'check_out',
        'formatted_total_office_time',
        'formatted_total_working_hour',
        'formatted_total_break_time',      # <-- added this
    )

    sortable_by = []


    def formatted_total_office_time(self, obj):
        return format_duration(obj.total_office_time)

    def formatted_total_working_hour(self, obj):
        return format_duration(obj.total_working_hour)

    def formatted_total_break_time(self, obj):
        return format_duration(obj.total_break_time)   # <-- new method

    formatted_total_office_time.short_description = 'Total Office Time'
    formatted_total_working_hour.short_description = 'Total Working Hour'
    formatted_total_break_time.short_description = 'Total Break Time'  # <-- new short desc

    # keep your existing code
    change_list_template = "admin/attendance/attendance/change_list.html"

    def changelist_view(self, request, extra_context=None):
        employees = Employee.objects.all()
        extra_context = extra_context or {}
        extra_context['employees'] = employees
        extra_context['selected_employee'] = request.GET.get('employee', '')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        employee_id = request.GET.get('employee')
        if employee_id:
            qs = qs.filter(employee__id=employee_id)
        return qs


def format_duration(duration):
    if not duration:
        return "-"
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'status', 'start_date', 'end_date', 'request_date', 'total_days_display')
    change_list_template = "admin/leave/leave/change_list.html"

    sortable_by = []

    def total_days_display(self, obj):
        return obj.get_leave_days_excluding_weekends()
    total_days_display.short_description = 'Total Days'

    def changelist_view(self, request, extra_context=None):
        employees = Employee.objects.all()
        extra_context = extra_context or {}
        extra_context['employees'] = employees
        extra_context['selected_employee'] = request.GET.get('employee__id__exact', '')
        extra_context['selected_date'] = request.GET.get('request_date__date', '')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        employee_id = request.GET.get('employee__id__exact')
        date = request.GET.get('request_date__date')

        if employee_id:
            qs = qs.filter(employee__id=employee_id)
        if date:
            qs = qs.filter(request_date__date=date)
        return qs

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        original_clean = form.clean

        def custom_clean(form_self):
            cleaned_data = original_clean(form_self)

            if cleaned_data.get('status') == 'Approved':
                employee = cleaned_data.get('employee')
                start_date = cleaned_data.get('start_date')
                end_date = cleaned_data.get('end_date')

                if employee and start_date and end_date:
                    # Calculate days excluding employee weekends
                    if obj:
                        days_requested = obj.get_leave_days_excluding_weekends()
                    else:
                        # For new leave (obj is None), calculate manually:
                        current_date = start_date
                        days_requested = 0
                        while current_date <= end_date:
                            day_name = current_date.strftime('%A')
                            if day_name not in employee.weekend:
                                days_requested += 1
                            current_date += timedelta(days=1)

                    current_status = obj.status if obj else None

                    if current_status != 'Approved':
                        leave_balance, _ = LeaveBalance.objects.get_or_create(
                            employee=employee,
                            defaults={"total_balance": 15}
                        )
                        if leave_balance.total_balance < days_requested:
                            raise ValidationError(
                                f"Cannot approve: {employee.name} has only {leave_balance.total_balance} days left, "
                                f"but requested {days_requested} days excluding weekends."
                            )
            return cleaned_data

        form.clean = custom_clean
        return form

    def save_model(self, request, obj, form, change):
        days_requested = obj.get_leave_days_excluding_weekends()

        leave_balance, _ = LeaveBalance.objects.get_or_create(
            employee=obj.employee,
            defaults={"total_balance": 15}
        )

        old_status = None
        old_days = 0
        if change:
            old_leave = Leave.objects.get(pk=obj.pk)
            old_status = old_leave.status
            old_days = old_leave.get_leave_days_excluding_weekends()

        leave_balance.refresh_from_db()

        adjustment = 0

        if obj.status == "Approved":
            if old_status != "Approved":
                adjustment = -days_requested
            elif old_days != days_requested:
                adjustment = -(days_requested - old_days)
        elif obj.status in ["Rejected", "Pending"]:
            if old_status == "Approved":
                adjustment = old_days

        if adjustment != 0:
            leave_balance.total_balance += adjustment
            leave_balance.total_balance = max(0, min(15, leave_balance.total_balance))
            leave_balance.save()

        # Send email notifications
        if not change or ("status" in form.changed_data) or ("start_date" in form.changed_data) or ("end_date" in form.changed_data):
            if obj.status == "Approved":
                subject = "Leave Approved"
                message = (
                    f"Dear {obj.employee.name},\n\n"
                    f"Your leave request from {obj.start_date} to {obj.end_date} has been APPROVED.\n\n"
                    f"Reason: {obj.reason}"
                )
            elif obj.status == "Rejected":
                subject = "Leave Rejected"
                message = (
                    f"Dear {obj.employee.name},\n\n"
                    f"Your leave request from {obj.start_date} to {obj.end_date} has been REJECTED.\n\n"
                    f"Reason: {obj.reason}"
                )
            elif obj.status == "Pending":
                subject = "Leave Status Changed to Pending"
                message = (
                    f"Dear {obj.employee.name},\n\n"
                    f"Your leave request from {obj.start_date} to {obj.end_date} has been changed to PENDING.\n\n"
                    f"Reason: {obj.reason}"
                )
            else:
                subject = None

            if subject:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [obj.employee.email])

        super().save_model(request, obj, form, change)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'total_balance')
    list_filter = ('total_balance',)
    search_fields = ('employee__name', 'employee__employee_id')

    sortable_by = []

    def has_add_permission(self, request):
        return False  # This hides the "Add" button



# Add this to your admin.py file

@admin.register(Break)
class BreakAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'break_start', 'break_end')

    sortable_by = []

    # Keep the custom template for top filters
    change_list_template = "admin/break/break/change_list.html"

    # Use built-in filtering logic but with custom display
    def changelist_view(self, request, extra_context=None):
        employees = Employee.objects.all()
        extra_context = extra_context or {}
        extra_context['employees'] = employees
        extra_context['selected_employee'] = request.GET.get('employee__id__exact', '')
        extra_context['selected_date'] = request.GET.get('date', '')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Employee filter
        employee_id = request.GET.get('employee__id__exact')
        if employee_id:
            qs = qs.filter(employee__id=employee_id)

        # Date filter
        date = request.GET.get('date')
        if date:
            qs = qs.filter(date=date)

        return qs

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)




from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('employee', 'floor', 'purpose', 'person_name', 'is_active', 'started_at', 'ended_at')

    sortable_by = []

    # Keep the custom template for top filters
    change_list_template = "admin/meeting/meeting/change_list.html"

    # Use built-in filtering logic but with custom display
    def changelist_view(self, request, extra_context=None):
        employees = Employee.objects.all()
        extra_context = extra_context or {}
        extra_context['employees'] = employees
        extra_context['selected_employee'] = request.GET.get('employee__id__exact', '')
        extra_context['selected_date'] = request.GET.get('started_at__date', '')
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Employee filter
        employee_id = request.GET.get('employee__id__exact')
        if employee_id:
            qs = qs.filter(employee__id=employee_id)

        # Date filter (filter by meeting start date)
        date = request.GET.get('started_at__date')
        if date:
            qs = qs.filter(started_at__date=date)

        return qs

    def employee_name(self, obj):
        return obj.employee.name if obj.employee else '(No Employee)'

    employee_name.short_description = 'Employee Name'



# Admin site header
admin.site.site_header = "Admin Panel"

# Inject global CSS
class GlobalMedia:
    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

AttendanceAdmin.__bases__ += (GlobalMedia,)
