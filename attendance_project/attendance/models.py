from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from django.core.validators import EmailValidator
from multiselectfield import MultiSelectField


class Employee(models.Model):
    employee_id = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    is_remote = models.BooleanField(default=False)
    email = models.EmailField(
        max_length=254,
        unique=True,
        null=True,  # You can decide if email is required or optional
        blank=True,
        validators=[EmailValidator()],
        help_text="Enter a valid email address"
    )
    birthday = models.DateField(null=True, blank=True)

    Designation_CHOICES = [
        ('Upsell', 'Upsell'),
        ('Front', 'Front'),
        ('Admin', 'Admin'),
        ('Book', 'Book'),
        ('Marketing', 'Marketing'),
        ('HR', 'HR'),
        ('Development', 'Development'),
        ('R&D', 'R&D'),
        ('Design', 'Design'),
        ('Production', 'Production'),
    ]
    designation = models.CharField(
        max_length=100,
        choices=Designation_CHOICES,
        blank=True,  # allow empty value
        null=True,  # allow DB to store NULL
        verbose_name='Department'
    )

    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Enter employee position (e.g., Junior Developer, Senior Developer, Manager)"
    )

    SHIFT_CHOICES = [
        ('3pm_to_12am', '3 PM to 12 AM'),
        ('4pm_to_1am', '4 PM to 1 AM'),
        ('5pm_to_2am', '5 PM to 2 AM'),
        ('6pm_to_3am', '6 PM to 3 AM'),
        ('7pm_to_4am', '7 PM to 4 AM'),
        ('8pm_to_5am', '8 PM to 5 AM'),
        ('9pm_to_6am', '9 PM to 6 AM'),
        ('10pm_to_7am', '10 PM to 7 AM'),
        ('12am_to_9am', '12 AM to 9 AM'),
        ('1am_to_10am', '1 AM to 10 AM'),
    ]
    shift = models.CharField(
        max_length=100,
        choices=SHIFT_CHOICES,
        default='8pm_to_5am',
    )

    WEEKEND_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    weekend = MultiSelectField(
        choices=WEEKEND_CHOICES,
        default=['Saturday', 'Sunday'],  # or empty list [] if no default
        blank=True,
        help_text="Select weekend days for this employee"
    )

    password = models.CharField(max_length=128, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_index=True)
    check_in = models.DateTimeField(null=True, blank=True, default=timezone.now)
    check_out = models.DateTimeField(null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    total_break_time = models.DurationField(null=True, blank=True)
    total_office_time = models.DurationField(null=True, blank=True)
    total_working_hour = models.DurationField(null=True, blank=True)

    STATUS_CHOICES = [
        ('On Time', 'On Time'),
        ('Late', 'Late'),
        ('Half Day', 'Half Day'),
        ('Absent', 'Absent'),
        ('Leave', 'Leave'),
        ('Weekend', 'Weekend'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        blank=True,
        null=True,  # <- Allow unset
    )

    def get_duration(self):
        if self.check_out:
            duration = self.check_out - self.check_in
            return str(duration).split('.')[0]  # Returns HH:MM:SS format
        return None

    def save(self, *args, **kwargs):
        if not self.date:
            now = self.check_in or timezone.now()

            # Define custom shift window: 12 PM to next day 12 PM
            noon_today = timezone.make_aware(datetime.combine(now.date(), time(12, 0)))
            noon_yesterday = noon_today - timedelta(days=1)
            noon_tomorrow = noon_today + timedelta(days=1)

            if now < noon_today:
                # Between 12 AM and 11:59 AM -> belongs to previous workday
                self.date = now.date() - timedelta(days=1)
            else:
                # From 12 PM onwards -> current workday
                self.date = now.date()

        # Auto-calculate status if not set
        if self.status is None:
            shift = self.employee.shift
            start_str = shift.split('_to_')[0]  # e.g., '3pm'

            try:
                start_time = datetime.strptime(start_str, "%I%p").time()
            except ValueError:
                raise ValueError(f"Invalid shift start format: {start_str}")

            shift_start_naive = datetime.combine(self.date, start_time)
            shift_start = timezone.make_aware(shift_start_naive)

            diff = self.check_in - shift_start

            if diff >= timedelta(hours=2):
                self.status = 'Half Day'
            elif diff > timedelta(minutes=15):
                self.status = 'Late'
            else:
                self.status = 'On Time'

        # ✅ Auto-calculate times when check_out is set
        if self.check_in and self.check_out:
            # Office time
            self.total_office_time = self.check_out - self.check_in

            # Breaks on same date for this employee
            breaks = Break.objects.filter(employee=self.employee, date=self.date)
            total_break = timedelta()
            for b in breaks:
                if b.break_start and b.break_end:
                    total_break += (b.break_end - b.break_start)

            self.total_break_time = total_break
            self.total_working_hour = self.total_office_time - total_break

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.status}"


from django.db import models
from django.utils import timezone
from datetime import timedelta


class Leave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_index=True)
    reason = models.TextField()
    request_date = models.DateTimeField(default=timezone.now)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    seen_by_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.name} - {self.start_date} to {self.end_date} - {self.status}"

    def get_leave_days_excluding_weekends(self):
        """
        Calculate total leave days excluding employee's weekend days.
        Assumes employee.weekend is a list of weekday names like ['Saturday', 'Sunday'].
        """
        if not self.start_date or not self.end_date:
            return 0

        employee_weekends = self.employee.weekend  # List of weekend day names

        total_days = 0
        current_date = self.start_date
        while current_date <= self.end_date:
            day_name = current_date.strftime('%A')  # Get day name like 'Monday'
            if day_name not in employee_weekends:
                total_days += 1
            current_date += timedelta(days=1)
        return total_days

    @property
    def total_days(self):
        # For backward compatibility, total_days returns days excluding weekends
        return self.get_leave_days_excluding_weekends()


class Break(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_index=True)
    break_start = models.DateTimeField(default=timezone.now)
    break_end = models.DateTimeField(null=True, blank=True)
    date = models.DateField(default=timezone.localdate)

    def __str__(self):
        return f"{self.employee.name} - {self.date} - Break"

    def end_break(self):
        self.break_end = timezone.now()
        self.save()

from django.contrib.auth import get_user_model


class Meeting(models.Model):
    floor = models.CharField(max_length=10)
    purpose = models.CharField(max_length=255)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='meetings')
    person_name = models.CharField(max_length=255, null=True, blank=True)  # Add this field
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Meeting {self.id} on Floor {self.floor} with {self.person_name or self.employee.name}"




class LeaveBalance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    total_balance = models.PositiveIntegerField(default=15)  # Single total balance

    def __str__(self):
        return f"{self.employee.name} - Total Balance: {self.total_balance}"

    def deduct_days(self, days):
        """Deduct days from total balance"""
        if self.total_balance >= days:
            self.total_balance -= days
            self.save()
            return True
        return False

    def add_days(self, days):
        """Add days back to total balance"""
        self.total_balance += days
        self.save()