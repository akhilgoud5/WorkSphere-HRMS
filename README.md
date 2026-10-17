# WorkSphere HRMS — Starter Project

A full-stack starter using FastAPI, SQLAlchemy, SQLite, React, and Vite.

## Requirements
- Python 3.10+
- Node.js 18+

## 1. Start the backend

Open a terminal in `WorkSphere/backend`:

### Windows
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

If PowerShell blocks activation, use:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to test the API.

## 2. Start the frontend

Open a SECOND terminal in `WorkSphere/frontend`:

```bash
npm install
npm run dev
```

Open the local URL Vite prints, usually http://localhost:5173.

## First test
1. Register a new employee account in the UI.
2. Sign in using that username and password.
3. Open the employee directory.
4. API docs: `GET /health`, `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, and employee endpoints.

## Important starter limitations
- This is the initial runnable foundation, not the finished seven-module assignment.
- Public registration only creates EMPLOYEE accounts. Do not expose HR/Admin role creation publicly.
- Employee create/update routes require HR or ADMIN. Employee deletion requires ADMIN.
- Attendance, leave, payroll, and notifications currently have frontend placeholder pages and need their database models, API routes, and workflows implemented in subsequent steps.
- Before deployment, set a strong random `SECRET_KEY` through environment variables, configure production CORS, use HTTPS, and review security settings.
