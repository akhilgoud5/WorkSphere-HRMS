# WorkSphere HRMS — Human Resource Management System

WorkSphere HRMS is a full-stack Human Resource Management System
built with FastAPI, Python, SQLAlchemy, SQLite, and React.

## Technologies Used

- Backend: Python, FastAPI
- Frontend: React, Vite
- Database: SQLite, SQLAlchemy
- Authentication: JWT
- API Documentation: Swagger UI

## Features

### Phase 1: Core HR Management
- User registration and login
- Role-based access control
- Employee management
- Attendance check-in and check-out
- Payroll management
- Leave management

### Phase 2: Advanced HR Features
- Role-based permissions
- Advanced employee and leave management

### Phase 3: Automation and Insights
- Shift management
- Leave calendar
- Document management

### Phase 4: Employee Experience and Integrations
- Employee onboarding
- Resignation and exit management
- Company announcements
- Task management
- Employee reports in CSV and PDF formats
- Employee feedback
- Employee profile management

## Backend Setup

Open a terminal in the `WorkSphere/backend` directory.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload