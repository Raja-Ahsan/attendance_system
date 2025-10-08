from django.apps import AppConfig

class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'

    def ready(self):
        # Start ZKTeco listener
        from .zk_runner import start_listener
        start_listener()

        # Import signals to activate them
        import attendance.signals
