from zk import ZK
import time
import requests
import threading
from datetime import timedelta
from django.utils import timezone  # Make sure Django is installed for this import

def zk_listener():
    DEVICE_IP = '192.168.18.116'
    DEVICE_PORT = 4370
    punch_map = {
        0: 'Check-in',
        1: 'Check-out',
        2: 'Break-out',
        3: 'Break-in',
        4: 'Overtime-in',
        5: 'Overtime-out'
    }
    API_URL = 'http://127.0.0.1:8000/fingerprint_data/'  # Django endpoint

    last_timestamp = None  # Track last processed log

    def make_aware_if_naive(dt):
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    while True:
        zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=10)
        conn = None

        try:
            print("🔗 Connecting to fingerprint device...")
            conn = zk.connect()
            conn.disable_device()
            print("✅ Device connected.")

            # --- STEP 1: Fetch all logs from last 24 hours on startup ---
            existing_attendance = conn.get_attendance()

            now = timezone.localtime()
            threshold_time = now - timedelta(hours=24)

            # ... inside zk_listener() ...

            if existing_attendance:
                recent_logs = [
                    att for att in existing_attendance
                    if make_aware_if_naive(att.timestamp) > threshold_time
                ]

                if recent_logs:
                    print(f"📅 Found {len(recent_logs)} logs in the last 24 hours. Processing...")
                    for att in sorted(recent_logs, key=lambda x: x.timestamp):
                        uid = att.user_id
                        timestamp = make_aware_if_naive(att.timestamp)
                        punch = getattr(att, 'punch', None)

                        if last_timestamp is None or timestamp > last_timestamp:
                            last_timestamp = timestamp

                        status = punch_map.get(punch, "Check-in")
                        print(f"[Startup Sync] {status} | User ID: {uid} at {timestamp}")

                        try:
                            response = requests.post(API_URL, data={
                                'punch_type': status,
                                'user_id': uid,
                                'timestamp': timestamp.isoformat()
                            })
                            if response.status_code != 200:
                                print(f"❌ Failed to sync log: {response.text}")
                        except Exception as e:
                            print("Error sending startup log to Django:", e)

                else:
                    print("ℹ️ No logs found in the last 24 hours.")
            else:
                print("ℹ️ No attendance logs found on device.")

            print("👂 Listening for new scans in real time...")

            # --- STEP 2: Keep listening for new scans ---
            while True:
                try:
                    attendance = conn.get_attendance()

                    for att in attendance:
                        uid = att.user_id
                        timestamp = make_aware_if_naive(att.timestamp)
                        punch = getattr(att, 'punch', None)

                        if last_timestamp and timestamp <= last_timestamp:
                            continue  # Skip already processed

                        last_timestamp = timestamp

                        status = punch_map.get(punch, "Check-in")
                        print(f"[{status}] User ID: {uid} at {timestamp}")

                        try:
                            response = requests.post(API_URL, data={
                                'punch_type': status,
                                'user_id': uid,
                                'timestamp': timestamp.isoformat()   # send real time
                            })
                            if response.status_code != 200:
                                print(f"❌ Failed to post data: {response.text}")
                        except Exception as e:
                            print("Error sending punch to Django:", e)

                    time.sleep(1)

                except Exception as loop_error:
                    print("Loop error:", loop_error)
                    break  # reconnect

        except Exception as e:
            print("❌ Device not reachable:", e)

        finally:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                    print("🔌 Disconnected from device.")
                except Exception as e:
                    print("Error during cleanup:", e)

        print("🔁 Retrying connection in 5 seconds...")
        time.sleep(5)


def start_listener():
    thread = threading.Thread(target=zk_listener, daemon=True)
    thread.start()