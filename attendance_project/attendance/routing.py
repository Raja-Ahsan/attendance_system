from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/admin-dashboard/$", consumers.DashboardConsumer.as_asgi()),  # 👈 matches JS
    re_path(r"ws/leave/$", consumers.LeaveNotificationConsumer.as_asgi()),
]
