import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("dashboard", self.channel_name)  # 👈 must be "dashboard"
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard", self.channel_name)

    # consumer.py
    async def send_attendance_update(self, event):
        data = event["data"]
        action = event.get("action")

        data["action"] = action  # Add action explicitly to message

        await self.send(text_data=json.dumps(data))




import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class LeaveNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("leave_notifications", self.channel_name)
        await self.accept()

        unseen = await self.get_unseen_count()
        await self.send(text_data=json.dumps({"unseen": unseen}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("leave_notifications", self.channel_name)

    async def leave_update(self, event):
        await self.send(text_data=json.dumps({
            "unseen": event["unseen"]
        }))

    @database_sync_to_async
    def get_unseen_count(self):
        from .models import Leave  # 👈 Moved import here
        return Leave.objects.filter(seen_by_admin=False).count()