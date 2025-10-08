from django import forms
from .models import Employee
from django.utils import timezone


class AttendanceReportForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        label="Select Employee"
    )

    # Choices for months (January to December)
    month = forms.ChoiceField(
        choices=[(str(i), timezone.datetime(2025, i, 1).strftime("%B")) for i in range(1, 13)],
        label="Select Month"
    )

    # Choices for years, e.g., from 2020 up to current year
    year = forms.ChoiceField(
        choices=[(str(y), str(y)) for y in range(2020, timezone.now().year + 1)],
        label="Select Year"
    )
