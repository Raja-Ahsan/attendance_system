from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from attendance.models import Employee, Attendance, Leave
from datetime import datetime

class Command(BaseCommand):
    help = 'Mark employees as Absent, Leave, or Weekend if not checked in by end of day (12PM-12PM cycle)'

    def handle(self, *args, **kwargs):
        now = timezone.localtime()
        today = now.date()

        # Shift day window if before 12 PM (use yesterday)
        if now.hour < 12:
            today = today - timedelta(days=1)

        # Get weekday name like 'Monday', 'Tuesday', etc.
        weekday_name = today.strftime('%A')

        employees = Employee.objects.all()

        for emp in employees:
            # Skip if already checked in or marked
            if Attendance.objects.filter(employee=emp, date=today).exists():
                continue

            # Check if today is employee's weekend day
            if weekday_name in emp.weekend:
                Attendance.objects.create(
                    employee=emp,
                    date=today,
                    status='Weekend',
                    check_in=None,
                    check_out=None
                )
                self.stdout.write(self.style.SUCCESS(f"{emp.name} marked as Weekend for {today}"))
                continue  # no need to check leave/absent

            # Check if admin set a leave for this employee on this date
            has_leave = Leave.objects.filter(
                employee=emp,
                status='Approved',
                start_date__lte=today,
                end_date__gte=today
            ).exists()

            if has_leave:
                # For Leave: Set check_in and check_out to None
                Attendance.objects.create(
                    employee=emp,
                    date=today,
                    status='Leave',
                    check_in=None,  # No check-in for leave
                    check_out=None  # No check-out for leave
                )
                self.stdout.write(self.style.SUCCESS(f"{emp.name} marked as Leave for {today}"))
            else:
                # For Absent: Set check_in and check_out to None
                Attendance.objects.create(
                    employee=emp,
                    date=today,
                    check_in=None,  # Set check-in to None for absent employee
                    check_out=None,  # Set check-out to None for absent employee
                    status='Absent'
                )
                self.stdout.write(self.style.WARNING(f"{emp.name} marked as Absent for {today}"))
