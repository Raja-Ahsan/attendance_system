Attendance System

C:\Users\home\PycharmProjects\PythonProject1: This is the project folder where our project is available.

C:\Users\home\PycharmProjects\PythonProject1\attendance_project\start_project.bat:  For Starting Attendance System and make sure that run as an Administrator.

C:\Users\home\PycharmProjects\PythonProject1\attendance_project\stop_project.bat: For stopping Project and make sure that run as an Administrator, We may not need to stop server because server start once and run for multiple days so there is no need to stop server daily.

C:\Users\home\PycharmProjects\PythonProject1\attendance_project\mark_absent.bat: For marking Absent, Leave and Weekend like we have to schedule it on almost ending time of office so that when this run it first check that those employees that are not present like they are absent or on leave or on weekend then by running this they are marked absent, leave, weekend for current day.

C:\Users\home\PycharmProjects\PythonProject1\attendance_project\backup.bat: For backup Data on daily basis. We must have to run this daily at the ending time of office, right after running backup file, by doing this data is backup on daily basis and store in both sql and dump format in backups folder as I show in video.

C:\Users\home\Documents\username_password.txt: This File contain user-id and password of almost all employees through which they login to their portal.

Admin Portal:  When the project is opened on a new PC for the first time, it will require login credentials before access. You must log in using the credentials stored in the credentials file path C:\Users\home\Documents\credentials.txt.
Once logged in, navigate to the User section to add a new admin account if needed.

New Employee Registration:
To register a new employee, two steps are required:
1.	First, the employee’s fingerprint must be enrolled, and an ID must be assigned to them in the ZKTeco machine.
2.	After that, using the same ID, the employee should be added to the attendance system, ensuring the ID matches the one assigned in the device.

 

Email Configuration (Gmail App Password Setup)
To enable email notifications (such as leave or attendance reports), you must configure Gmail using an App Password instead of your regular Gmail password.
Steps to Generate a 16-Character App Password:
1.	Open your Google Account and go to Security → Signing in to Google.
2.	Enable 2-Step Verification if it is not already turned on.
3.	After enabling it, go back to the Security page and select App Passwords.
4.	Choose Mail as the app and Other (Custom name) → e.g., AttendanceApp.
5.	Click Generate, and Google will display a 16-character password.
6.	Copy this password — it will only be shown once.
Usage in Project:
•	Use your Gmail address as EMAIL_HOST_USER.
•	Use the generated App Password (16 characters) as EMAIL_HOST_PASSWORD.
•	This configuration allows the system to send emails for leave or attendance reports automatically.

Remote Employees: Check-In and Check-out are given on their employee dashboard so they do this by 1st login to their account and then perform action. Remember when adding new employee then there is the option of either employee is Remote or not so admin has to select checkbox to set employee as admin.

Scheduling (Optional):
You can automate these scripts using the Windows Task Scheduler.
By scheduling them, you won’t need to manually start or stop the project every day.
For example:
•	Schedule backup.bat and mark_absent.bat to run automatically at the end of the day.
•	If desired, you can also schedule start_project.bat to start the system automatically each morning.


 

System Access via Tailscale – Instructions
Summary:
Our internal system is running at the IP address: http://100.100.70.122:8000
•	Employee portal: http://100.100.70.122:8000
•	Admin portal: http://100.100.70.122:8000/admin
This server is only accessible through Tailscale VPN (Tailnet). You must be connected to our Tailnet using the authorized Gmail account (e.g. testing71522@gmail.com) as shown in the screenshot.
________________________________________
Step-by-Step Guide (For both Employees & Admins)
1. Install Tailscale (if not already installed)
•	Download and install Tailscale from https://tailscale.com on your Windows, Mac, or Linux system.
•	Once installed, launch the Tailscale app.
2. Login with the same Gmail account used in our Tailnet
•	Sign in to Tailscale using the authorized Gmail account (testing71522@gmail.com, or the one approved in your organization’s Tailnet).
•	Once logged in, Tailscale should show “Connected” (as shown in the screenshot), and your device will get a private Tailscale IP (e.g. 100.100.70.x).
3. Verify Connection
•	Open the Tailscale app and ensure your device is connected.
•	Once connected, open the browser and access:
o	Employee portal: http://100.100.70.122:8000
o	Admin portal: http://100.100.70.122:8000/admin (only for authorized admin users)
4. Accessing from another PC
•	Install Tailscale on that PC.
•	Log in using the same Gmail account registered in the Tailnet.
•	Once connected, you’ll be able to access the same internal system from the new PC using the same URLs.
⚠️ Important: If you use a different Gmail account not part of our Tailnet, access will be denied.
