cd C:\Apps\timetable
start python.exe manage.py runserver
timeout /t 4
start http://127.0.0.1:8000/admin/
