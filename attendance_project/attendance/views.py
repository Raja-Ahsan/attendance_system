from .employee_registry import EMPLOYEE_DATA
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from .models import Leave, LeaveBalance, Employee, Attendance, Break, Meeting
from django.core.mail import EmailMessage
from io import BytesIO
import json
from django.core.mail import send_mail
from django.conf import settings
from .forms import AttendanceReportForm
from django.shortcuts import redirect, get_object_or_404, render
from django.template import Template, Context
from django.http import JsonResponse
from datetime import time, timedelta, datetime
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.utils.timezone import now
from collections import defaultdict
from django.http import JsonResponse
from django.db.models import Prefetch
from datetime import date  # Assuming `get_shift_adjusted_date()` uses datetime

from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime


def get_shift_adjusted_date(now=None):
    if now is None:
        now = timezone.localtime()
    else:
        # Ensure now is aware in local timezone for proper comparison
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone.get_current_timezone())
        else:
            now = timezone.localtime(now)

    noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

    if now < noon:
        return (now - timedelta(days=1)).date()
    else:
        return now.date()



@csrf_exempt
def fingerprint_data_view(request):
    print("🔴 Received fingerprint POST request")

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

    punch_type = request.POST.get("punch_type")
    user_id = request.POST.get("user_id")
    timestamp_str = request.POST.get("timestamp")

    print(f"📥 Fingerprint Data: {punch_type}, User ID: {user_id}")

    employee = None

    # Try fetching from DB first
    try:
        employee = Employee.objects.get(employee_id=user_id)
        print(f"✅ Employee {employee.name} found in DB")
    except Employee.DoesNotExist:
        print("ℹ️ Employee not found in DB, checking dictionary...")
        #
        # # Fallback: try from dictionary
        # emp_data = EMPLOYEE_DATA.get(user_id)
        # if emp_data:
        #     print(f"✅ Found in registry. Creating new employee with ID {user_id}")
        #     employee = Employee.objects.create(
        #         employee_id=user_id,
        #         # name=emp_data["name"],
        #         # designation=emp_data["designation"],
        #         # position=emp_data["position"],
        #         # shift=emp_data["shift"],
        #     )
        # else:
        #     print("❌ ID not in dictionary")
        #     return JsonResponse({
        #         "status": "error",
        #         "message": "Employee not registered in system or dictionary"
        #     }, status=404)

    # Parse timestamp to aware datetime, fallback to now
    punch_time = parse_datetime(timestamp_str)
    if punch_time is None:
        punch_time = timezone.now()
    elif timezone.is_naive(punch_time):
        punch_time = timezone.make_aware(punch_time)

    # Proceed with attendance marking
    if punch_type == "Check-in":
        perform_check_in(employee, punch_time)

    elif punch_type == "Check-out":
        perform_check_out(employee, punch_time)
    else:
        return JsonResponse({"status": "error", "message": "Invalid punch type"}, status=400)

    return JsonResponse({"status": "success"})

def login_view(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        password = request.POST.get('password')

        try:
            employee = Employee.objects.get(employee_id=emp_id)
            if check_password(password, employee.password):
                today = get_shift_adjusted_date()
                attendance = Attendance.objects.filter(employee=employee, date=today).first()

                if employee.is_remote:
                    # ✅ Remote employees can go directly to dashboard
                    request.session['employee_id'] = employee.employee_id
                    return redirect('dashboard')

                # 👇 For non-remote employees, keep the old rule
                if attendance and attendance.check_in:
                    request.session['employee_id'] = employee.employee_id
                    return redirect('dashboard')
                else:
                    return render(request, 'login.html', {
                        'error': 'You need to check in first through the fingerprint machine.'
                    })
            else:
                return render(request, 'login.html', {'error': 'Invalid password'})
        except Employee.DoesNotExist:
            return render(request, 'login.html', {'error': 'Employee not found'})

    return render(request, 'login.html')



from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def remote_checkin(request):
    emp_id = request.session.get('employee_id')
    if not emp_id:
        return redirect('login')

    employee = Employee.objects.get(employee_id=emp_id)
    today = get_shift_adjusted_date()

    attendance, _ = Attendance.objects.get_or_create(employee=employee, date=today)
    if not attendance.check_in:
        attendance.check_in = now()
        attendance.status = "Remote"
        attendance.save()

    # ✅ Redirect to employee_home instead of dashboard
    return redirect('employee_home')



@csrf_exempt
def remote_checkout(request):
    emp_id = request.session.get('employee_id')
    if not emp_id:
        return redirect('login')

    employee = Employee.objects.get(employee_id=emp_id)
    today = get_shift_adjusted_date()
    attendance = Attendance.objects.filter(employee=employee, date=today).first()

    if attendance and not attendance.check_out:
        attendance.check_out = now()
        attendance.save()

    # ✅ Redirect to employee_home instead of dashboard
    return redirect('employee_home')



# views.py - Updated to work with single total balance

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from datetime import datetime


def dashboard_view(request):
    emp_id = request.session.get('employee_id')
    if not emp_id:
        return redirect('login')

    employee = Employee.objects.get(employee_id=emp_id)
    today = get_shift_adjusted_date()
    attendance = Attendance.objects.filter(employee=employee, date=today).first()

    break_record = Break.objects.filter(employee=employee, date=today, break_end=None).first()
    status = attendance.status if attendance else None
    latest_leave = Leave.objects.filter(employee=employee).order_by('-request_date').first()

    # Get or create single leave balance
    leave_balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        defaults={"total_balance": 15}
    )

    return render(request, 'dashboard.html', {
        "employee": employee,
        "attendance": attendance,
        "break": break_record,
        "status": status,
        "latest_leave": latest_leave,
        "total_leave_balance": leave_balance.total_balance,  # Single balance
    })


def employee_dashboard(request):
    if not request.session.get("employee_id"):
        return redirect("employee_login")
    return render(request, "employee_dashboard.html")


def employee_home(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("employee_login")

    employee = get_object_or_404(Employee, employee_id=emp_id)
    today = get_shift_adjusted_date()
    attendance = Attendance.objects.filter(employee=employee, date=today).first()

    # Check if employee is on approved leave today
    if Leave.objects.filter(
            employee=employee,
            status="Approved",
            start_date__lte=today,
            end_date__gte=today
    ).exists():
        status = "Leave"
    elif attendance and attendance.check_in:
        status = attendance.status
    else:
        status = "Absent"

    latest_leave = Leave.objects.filter(employee=employee).order_by("-id").first()

    # Get or create single leave balance
    leave_balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        defaults={"total_balance": 15}
    )

    # 👇 Add context for remote employee check
    can_checkin = employee.is_remote and (not attendance or not attendance.check_in)
    can_checkout = employee.is_remote and attendance and attendance.check_in and not attendance.check_out

    context = {
        "employee": employee,
        "attendance": attendance,
        "status": status,
        "latest_leave": latest_leave,
        "break": Break.objects.filter(employee=employee, date=today, break_end=None).first(),
        "total_leave_balance": leave_balance.total_balance,
        "is_remote": employee.is_remote,  # ✅ pass this to the template
        "can_checkin": can_checkin,
        "can_checkout": can_checkout,
        "status_message": "You're checked in!" if attendance and attendance.check_in else "",
    }
    return render(request, "employee_home.html", context)


def perform_check_in(employee, punch_time):
    today = get_shift_adjusted_date(punch_time)

    att, created = Attendance.objects.get_or_create(
        employee=employee,
        date=today,
        defaults={'check_in': punch_time}
    )

    if not created:
        if not att.check_in or att.check_in > punch_time:
            att.check_in = punch_time
            print(f"DEBUG perform_check_in setting check_in={punch_time}")
            att.save()


def calculate_and_save_working_times(attendance):
    if attendance.check_in and attendance.check_out:
        total_office = attendance.check_out - attendance.check_in

        breaks = Break.objects.filter(
            employee=attendance.employee,
            break_start__gte=attendance.check_in,
            break_end__lte=attendance.check_out,
        )
        total_break = timedelta()

        print(f"Calculating breaks for employee {attendance.employee} on date {attendance.date}")
        print(f"Found breaks: {breaks.count()}")

        for b in breaks:
            print(f"Break start: {b.break_start}, Break end: {b.break_end}")
            if b.break_start and b.break_end:
                total_break += b.break_end - b.break_start

        total_working = total_office - total_break if total_office > total_break else timedelta()

        print(f"Total office time: {total_office}")
        print(f"Total break time: {total_break}")
        print(f"Total working time: {total_working}")

        attendance.total_office_time = total_office
        attendance.total_working_hour = total_working
        attendance.total_break_time = total_break
        attendance.save()


def perform_check_out(employee, punch_time):
    today = get_shift_adjusted_date(punch_time)

    att, created = Attendance.objects.get_or_create(
        employee=employee,
        date=today,
    )

    # ❗ Do NOT overwrite existing check-out
    if not att.check_out:
        att.check_out = punch_time
        print(f"✅ perform_check_out: setting check_out = {punch_time}")
        att.save()
    else:
        print(f"⚠️ Check-out already exists: {att.check_out}, ignoring new check-out at {punch_time}")



from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.dateparse import parse_date
import traceback

def calculate_days_excluding_weekends(employee, start_date, end_date):
    current_date = start_date
    total_days = 0
    employee_weekends = employee.weekend  # e.g. ['Saturday', 'Sunday']
    while current_date <= end_date:
        if current_date.strftime('%A') not in employee_weekends:
            total_days += 1
        current_date += timedelta(days=1)
    return total_days

@csrf_exempt
def request_leave_view(request):
    try:
        if request.method == "POST":
            emp_id = request.session.get('employee_id')
            if not emp_id:
                return redirect('login')

            employee = get_object_or_404(Employee, employee_id=emp_id)
            reason = request.POST.get("reason", "").strip()
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")

            if not start_date or not end_date:
                return HttpResponse("Start date and end date are required.", status=400)

            try:
                start = parse_date(start_date)
                end = parse_date(end_date)
                if start > end:
                    return HttpResponse("Start date cannot be after end date.", status=400)
            except Exception:
                return HttpResponse("Invalid dates.", status=400)

            days_requested = calculate_days_excluding_weekends(employee, start, end)

            leave_balance = LeaveBalance.objects.filter(employee=employee).first()
            if leave_balance is None:
                return HttpResponse("You do not have any leave balance available.", status=400)

            if leave_balance.total_balance < days_requested:
                return HttpResponse(f"Not enough leaves remaining. You have {leave_balance.total_balance} left.", status=400)

            Leave.objects.create(
                employee=employee,
                reason=reason,
                start_date=start,
                end_date=end,
                status='Pending'  # balance deducted on approval
            )

            notify_leave_update()  # ✅ Real-time notification to admin WebSocket

            return HttpResponse("Leave request submitted successfully.")

        return redirect('dashboard')

    except Exception:
        error_message = traceback.format_exc()
        return HttpResponse(f"An error occurred:<br><pre>{error_message}</pre>", status=500)


from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Leave

@require_GET
def unseen_leave_count_api(request):
    count = Leave.objects.filter(seen_by_admin=False).count()
    return JsonResponse({"unseen": count})

@csrf_exempt
@require_POST
def reset_unseen_leave_api(request):
    Leave.objects.filter(seen_by_admin=False).update(seen_by_admin=True)
    return JsonResponse({"success": True})

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Leave

def notify_leave_update():
    unseen = Leave.objects.filter(seen_by_admin=False).count()
    print(f"[notify_leave_update] Sending unseen count: {unseen}")  # ✅ Debug log
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "leave_notifications",
        {"type": "leave_update", "unseen": unseen}
    )



@csrf_exempt
def start_break_view(request):
    if request.method == "POST":
        emp_id = request.session.get('employee_id')
        if not emp_id:
            return redirect('login')

        employee = Employee.objects.get(employee_id=emp_id)
        today = get_shift_adjusted_date()


        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        if not attendance or not attendance.check_in:
            return HttpResponse("You need to check in before starting a break.", status=400)

        existing_break = Break.objects.filter(employee=employee, date=today, break_end=None).first()
        if existing_break:
            return HttpResponse("Break already started.")

        # Actually create a new break and save (to trigger signal)
        new_break = Break.objects.create(
            employee=employee,
            date=today,
            break_start=timezone.now()
        )

        return HttpResponse("<script>window.top.location.href='/dashboard/';</script>")

# End break view with WebSocket event
@csrf_exempt
def end_break_view(request):
    if request.method == "POST":
        emp_id = request.session.get('employee_id')
        if not emp_id:
            return redirect('login')

        employee = Employee.objects.get(employee_id=emp_id)
        today = get_shift_adjusted_date()


        try:
            break_record = Break.objects.get(employee=employee, date=today, break_end=None)
            break_record.break_end = timezone.now()
            break_record.save()


            return HttpResponse("<script>window.top.location.href='/dashboard/';</script>")

        except Break.DoesNotExist:
            return HttpResponse("No active break found.")

def admin_dashboard_view(request):
    return render(request, "admin_dashboard.html")

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.utils import timezone  # important for localtime conversion


def format_duration(duration):
    if not duration:
        return "-"
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_datetime_local(dt):
    if not dt:
        return "-"
    local_dt = timezone.localtime(dt)
    return local_dt.strftime('%I:%M %p')


def generate_attendance_report_pdf(employee, records, month_year_str):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='CenteredTitle', parent=styles['Title'], alignment=1)
    subtitle_style = ParagraphStyle(name='CenteredSubTitle', parent=styles['Heading2'], alignment=1)

    elements = []

    # Title and subtitle
    elements.append(Paragraph(f"Attendance Report for {employee.name}", title_style))
    elements.append(Paragraph(f"Month: {month_year_str}", subtitle_style))
    elements.append(Spacer(1, 20))

    # Summary calculations (Removed total time rows)
    total_days = records.exclude(status__iexact='').count()
    total_ontime = records.filter(status__iexact='On Time').count()
    total_late = records.filter(status__iexact='Late').count()
    total_leave = records.filter(status__iexact='Leave').count()
    total_halfday = records.filter(status__iexact='Half Day').count()
    total_absent = records.filter(status__iexact='Absent').count()

    summary_data = [
        ['Summary', 'Count'],
        ['Total Days', total_days],
        ['On Time', total_ontime],
        ['Late', total_late],
        ['Leave', total_leave],
        ['Half Day', total_halfday],
        ['Absent', total_absent],
    ]
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4b72c2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Attendance details table
    data = [['Date', 'Check In', 'Check Out', 'Status', 'Office Time', 'Break Time', 'Working Hour']]
    for rec in records:
        if rec.status.lower() in ['leave', 'absent']:
            check_in_str = check_out_str = '-'
        else:
            check_in_str = format_datetime_local(rec.check_in)
            check_out_str = format_datetime_local(rec.check_out)

        data.append([
            rec.date.strftime('%b %d, %Y'),
            check_in_str,
            check_out_str,
            rec.status,
            format_duration(rec.total_office_time),
            format_duration(rec.total_break_time),   # Make sure your Attendance model has this field!
            format_duration(rec.total_working_hour),
        ])

    attendance_table = Table(data, colWidths=[80, 70, 70, 80, 80, 80, 80])
    attendance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4b72c2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(attendance_table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_attendance_pdf(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        month = int(request.POST.get('month'))
        year = datetime.now().year

        employee = Employee.objects.get(id=employee_id)
        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        records = Attendance.objects.filter(
            employee=employee,
            date__gte=start_date,
            date__lt=end_date
        ).order_by('date')

        month_year_str = start_date.strftime('%B %Y')
        pdf = generate_attendance_report_pdf(employee, records, month_year_str)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{employee.name}_{start_date.strftime("%B")}.pdf"'
        response.write(pdf)
        return response



from django.shortcuts import render, redirect, get_object_or_404
from .models import Employee, Leave

def leave_history_view(request):
    employee_id = request.session.get('employee_id')
    if not employee_id:
        return redirect('login')

    employee = get_object_or_404(Employee, employee_id=employee_id)

    selected_year = request.GET.get("year")
    selected_month = request.GET.get("month")

    leave_history = Leave.objects.none()

    if selected_year and selected_month:
        try:
            year = int(selected_year)
            month = int(selected_month)

            leave_history = Leave.objects.filter(
                employee=employee,
                request_date__year=year,
                request_date__month=month,
            ).order_by('-request_date')
        except ValueError:
            leave_history = Leave.objects.none()

    available_years = (
        Leave.objects.filter(employee=employee)
        .dates("request_date", "year")
    )
    available_years = sorted({d.year for d in available_years}, reverse=True)

    context = {
        "employee": employee,
        "leave_history": leave_history,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "available_years": available_years,
    }

    return render(request, "leave_history.html", context)


def attendance_history_view(request):
    emp_id = request.session.get('employee_id')
    if not emp_id:
        return redirect('login')

    employee = Employee.objects.get(employee_id=emp_id)

    # Get selected year & month from query params
    selected_year = request.GET.get("year")
    selected_month = request.GET.get("month")

    attendance_history = []
    break_history = []

    if selected_year and selected_month:
        attendance_history = Attendance.objects.filter(
            employee=employee,
            date__year=selected_year,
            date__month=selected_month
        ).order_by('-date')

        break_history = Break.objects.filter(
            employee=employee,
            date__year=selected_year,
            date__month=selected_month
        ).order_by('-break_start')

    # Collect distinct available years for dropdown
    available_years = Attendance.objects.filter(employee=employee).dates("date", "year")
    available_years = sorted({d.year for d in available_years}, reverse=True)

    # Months list (1–12)
    months = [(i, datetime(2000, i, 1).strftime("%B")) for i in range(1, 13)]

    return render(request, "attendance_history.html", {
        "employee": employee,
        "attendance_history": attendance_history,
        "break_history": break_history,
        "available_years": available_years,
        "months": months,
        "selected_year": int(selected_year) if selected_year else None,
        "selected_month": int(selected_month) if selected_month else None,
    })


def get_today_dashboard_data(request):
    today = get_shift_adjusted_date()
    data = {}

    # Prefetch related employee to avoid repeated DB hits
    attendance_qs = Attendance.objects.select_related('employee').filter(date=today)
    break_qs = Break.objects.select_related('employee').filter(date=today)

    # First: Process Attendance
    for att in attendance_qs:
        employee = att.employee
        if not employee:
            continue  # skip if employee is missing

        key = employee.employee_id

        data[key] = {
            "employee_id": key,
            "employee": employee.name,
            "designation": employee.designation,
            "position": employee.position,
            "check_in": att.check_in.isoformat() if att.check_in else None,
            "check_out": att.check_out.isoformat() if att.check_out else None,
            "break_starts": [],
            "break_ends": [],
        }

    # Second: Process Breaks
    for br in break_qs:
        employee = br.employee
        if not employee:
            continue  # skip if employee is missing

        key = employee.employee_id

        # Ensure entry exists even if no attendance
        if key not in data:
            data[key] = {
                "employee_id": key,
                "employee": employee.name,
                "designation": employee.designation,
                "position": employee.position,
                "check_in": None,
                "check_out": None,
                "break_starts": [],
                "break_ends": [],
            }

        if br.break_start:
            data[key]["break_starts"].append(br.break_start.isoformat())
        if br.break_end:
            data[key]["break_ends"].append(br.break_end.isoformat())

    return JsonResponse({"attendance": data})

def generate_attendance_report(request):
    form = AttendanceReportForm()
    return render(request, 'generate_report.html', {'form': form})

from datetime import datetime
from django.shortcuts import render, redirect
from .models import Attendance
from .forms import AttendanceReportForm  # assuming you have this form

def format_datetime(dt):
    if not dt:
        return "-"
    month = dt.strftime('%b')
    day = dt.day  # no leading zero
    year = dt.year
    time_str = dt.strftime('%I:%M %p').lstrip('0').lower()
    return f"{month} {day}, {year}, {time_str}"


from django.db.models import Q
from datetime import datetime
from django.utils.timezone import localtime



def view_monthly_report(request):
    if request.method == 'POST':
        form = AttendanceReportForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            records = Attendance.objects.filter(
                employee=employee,
                date__gte=start_date,
                date__lt=end_date
            ).order_by('date')

            # Summary counts
            total_days = records.exclude(status__iexact='').count()
            total_ontime = records.filter(status__iexact='On Time').count()
            total_late = records.filter(status__iexact='Late').count()
            total_leave = records.filter(status__iexact='Leave').count()
            total_halfday = records.filter(status__iexact='Half Day').count()
            total_absent = records.filter(status__iexact='Absent').count()

            summary = {
                'Total Days': total_days,
                'On Time': total_ontime,
                'Late': total_late,
                'Leave': total_leave,
                'Half Day': total_halfday,
                'Absent': total_absent,
            }

            # Format records for display
            formatted_records = []
            for rec in records:
                if rec.status.lower() in ['leave', 'absent']:
                    check_in_str = "-"
                    check_out_str = "-"
                else:
                    check_in_str = format_datetime(localtime(rec.check_in)) if rec.check_in else "-"
                    check_out_str = format_datetime(localtime(rec.check_out)) if rec.check_out else "-"

                formatted_records.append({
                    'date': rec.date.strftime("%b %d, %Y"),
                    'check_in': check_in_str,
                    'check_out': check_out_str,
                    'status': rec.status,
                    'total_office_time': format_duration(rec.total_office_time),
                    'total_break_time': format_duration(rec.total_break_time),
                    'total_working_hour': format_duration(rec.total_working_hour),
                })

            return render(request, 'monthly_report.html', {
                'records': formatted_records,
                'employee': employee,
                'month': month,
                'month_name': start_date.strftime('%B'),
                'year': year,
                'summary': summary,
            })

    return redirect('generate_attendance_report')



def send_attendance_report_via_email(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        month = int(request.POST.get('month'))
        year = datetime.now().year

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return HttpResponse("Employee not found.", status=404)

        # Check if employee has an email
        if not employee.email:
            return HttpResponse(
                '<p style="color:white;">Employee does not have an email address.</p>',
                status=400
            )

        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        records = Attendance.objects.filter(
            employee=employee,
            date__gte=start_date,
            date__lt=end_date
        ).order_by('date')

        month_year_str = start_date.strftime('%B %Y')
        pdf = generate_attendance_report_pdf(employee, records, month_year_str)

        subject = f'Attendance Report for {employee.name} - {month_year_str}'
        body = 'Please find attached your attendance report.'

        email = EmailMessage(
            subject,
            body,
            settings.EMAIL_HOST_USER,
            [employee.email],
        )
        email.attach(
            f'attendance_report_{start_date.strftime("%B_%Y")}.pdf',
            pdf,
            'application/pdf'
        )
        email.send(fail_silently=False)

        return HttpResponse(
            '<p style="color:white;">Attendance report sent via email successfully.</p>'
        )

    return HttpResponse("Invalid request", status=400)


def get_shift_adjusted_datetime_range(now=None):
    now = now or timezone.localtime()
    noon_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now < noon_today:
        start = noon_today - timedelta(days=1)
        end = noon_today
    else:
        start = noon_today
        end = noon_today + timedelta(days=1)
    return start, end

def quick_view_dashboard(request):
    start, end = get_shift_adjusted_datetime_range()

    employees_data = []
    employees = Employee.objects.all()

    # Get current date for weekend check
    current_date = start.date()

    for emp in employees:
        attendance = Attendance.objects.filter(employee=emp, check_in__gte=start, check_in__lt=end).first()

        leave = Leave.objects.filter(
            employee=emp,
            start_date__lte=current_date,
            end_date__gte=current_date,
            status="Approved"
        ).first()

        emp_break = Break.objects.filter(employee=emp).order_by('-break_start').first()

        # Check if today is employee's weekend
        # Employee.weekend is a list of day names e.g. ['Saturday', 'Sunday']
        weekday_name = current_date.strftime('%A')  # e.g., "Monday"
        is_weekend = weekday_name in emp.weekend

        employees_data.append({
            "employee_id": emp.employee_id,
            "name": emp.name,
            "department": emp.designation,
            "birthday": emp.birthday.isoformat() if emp.birthday else None,
            "status": "leave" if leave else None,
            "check_in": attendance.check_in.isoformat() if attendance and attendance.check_in else None,
            "check_out": attendance.check_out.isoformat() if attendance and attendance.check_out else None,
            "break_start": emp_break.break_start.isoformat() if emp_break and emp_break.break_start else None,
            "break_end": emp_break.break_end.isoformat() if emp_break and emp_break.break_end else None,
            "is_weekend": is_weekend,
        })

    return render(request, "quick_view_dashboard.html", {
        "employees_json": json.dumps(employees_data)
    })


def active_meeting_api(request):
    employee_id = request.GET.get('employee_id')
    try:
        meeting = Meeting.objects.filter(employee__employee_id=employee_id, is_active=True).first()
        if meeting:
            data = {
                'id': meeting.id,
                'floor': meeting.floor,
                'purpose': meeting.purpose,
                'person_name': meeting.person_name,
                'started_at': meeting.started_at.isoformat(),
            }
            return JsonResponse({'active_meeting': data})
        else:
            return JsonResponse({'active_meeting': None})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




@csrf_exempt
def start_meeting(request):
    if request.method == "POST":
        floor = request.POST.get('floor')
        purpose = request.POST.get('purpose')
        person_name = request.POST.get('person_name')
        employee_id = request.POST.get('employee_id')

        employee = Employee.objects.get(employee_id=employee_id)

        # Check if an active meeting exists
        active_meeting = Meeting.objects.filter(employee=employee, is_active=True).first()
        if active_meeting:
            return JsonResponse({'status': 'error', 'message': 'You already have an active meeting.'})

        # Create new meeting
        meeting = Meeting.objects.create(
            floor=floor,
            purpose=purpose,
            employee=employee,
            person_name=person_name,
            is_active=True
        )
        return JsonResponse({'status': 'started', 'meeting_id': meeting.id})


@csrf_exempt
def end_meeting(request):
    if request.method == 'POST':
        # Accept JSON body or form POST
        try:
            data = json.loads(request.body)
            employee_id = data.get('employee_id')
        except Exception:
            employee_id = request.POST.get('employee_id')

        if not employee_id:
            return JsonResponse({'status': 'error', 'message': 'Employee ID is required.'})

        try:
            # Use double underscore to lookup related employee field
            meeting = Meeting.objects.get(employee__employee_id=employee_id, is_active=True)
            meeting.is_active = False
            meeting.ended_at = now()
            meeting.save()
            return JsonResponse({'status': 'ended'})
        except Meeting.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Active meeting not found for this employee.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
