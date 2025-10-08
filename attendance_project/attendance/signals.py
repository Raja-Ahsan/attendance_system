from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Attendance, Break, Leave
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Existing attendance signal
@receiver(post_save, sender=Attendance)
def broadcast_attendance_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    data = {
        "employee": instance.employee.name,
        "employee_id": instance.employee.employee_id,
        "designation": instance.employee.designation,
        "position": instance.employee.position,


    }

    if created:
        data.update({
            "check_in": str(instance.check_in),
            "status": instance.status,
        })
        action = "check_in"
    elif instance.check_out:
        data.update({
            "check_out": str(instance.check_out),
            "duration": instance.get_duration(),
        })
        action = "check_out"
    else:
        return

    async_to_sync(channel_layer.group_send)(
        "dashboard",
        {
            "type": "send_attendance_update",
            "data": data,
            "action": action,
        }
    )


@receiver(post_save, sender=Break)
def broadcast_break_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    employee_name = instance.employee.name
    position = instance.employee.position  # Ensure this is included
    designation = instance.employee.designation  # Ensure this is included

    if created:
        action = "break_start"
        time = str(instance.break_start)
    elif instance.break_end:
        action = "break_end"
        time = str(instance.break_end)
    else:
        return

    data = {
        "employee_id": instance.employee.employee_id,  # Add this line
        "employee": employee_name,
        "designation": designation,
        "position": position,
        "time": time,
    }

    async_to_sync(channel_layer.group_send)(
        "dashboard",
        {
            "type": "send_attendance_update",
            "data": data,
            "action": action,
        }
    )


# attendance/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Employee, LeaveBalance

@receiver(post_save, sender=Employee)
def create_leave_balance(sender, instance, created, **kwargs):
    if created:
        # Create LeaveBalance with default total_balance (e.g., 15)
        LeaveBalance.objects.create(employee=instance, total_balance=15)


# @receiver(post_save, sender=Leave)
# def broadcast_leave_request(sender, instance, created, **kwargs):
#     if not created:
#         return
#
#     channel_layer = get_channel_layer()
#     position = instance.employee.position  # Ensure this is included
#     designation = instance.employee.designation  # Ensure this is included
#
#     data = {
#         "employee": instance.employee.name,
#         "designation": designation,
#         "position": position,  # Include position here
#         # "time": str(instance.timestamp),  # Assuming there's a timestamp on Leave
#         "reason": instance.reason,
#     }
#
#     async_to_sync(channel_layer.group_send)(
#         "dashboard",
#         {
#             "type": "send_attendance_update",
#             "data": data,
#             "action": "leave_request",
#         }
#     )
