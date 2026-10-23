
import React, { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useNavigate,
} from "react-router-dom";
import axios from "axios";
import "./style.css";

const API = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("worksphere_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || JSON.stringify(item))
      .join(", ");
  }

  if (typeof detail === "string") return detail;
  if (detail) return JSON.stringify(detail);

  return error?.message || "Request failed. Check that the backend is running.";
}

// ---------------- LOGIN ----------------

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const body = new URLSearchParams();
      body.append("username", username.trim());
      body.append("password", password);

      const response = await api.post("/auth/login", body, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      const token =
        response.data?.access_token || response.data?.token;

      if (!token) {
        throw new Error("Login response did not contain an access token.");
      }

      localStorage.setItem("worksphere_token", token);

      const userData = response.data?.user || {
        username: username.trim(),
      };

      onLogin(userData);
      navigate("/", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-icon">▣</div>
        <p className="brand">WORKSPHERE HRMS</p>
        <h1>Welcome back</h1>
        <p className="muted">
          Your workplace, organized in one place.
        </p>

        <label htmlFor="login-username">Username</label>
        <input
          id="login-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter username"
          autoComplete="username"
          required
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
          autoComplete="current-password"
          required
        />

        {error && <p className="error">{error}</p>}

        <button disabled={loading} type="submit">
          {loading ? "Signing in..." : "Sign in"}
        </button>

        <p className="muted">
          New to WorkSphere? <Link to="/register">Create account</Link>
        </p>
      </form>
    </main>
  );
}

// ---------------- REGISTER ----------------

function Register() {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.post("/auth/register", form);

      setMessage("Account created successfully. Please sign in.");

      window.setTimeout(() => {
        navigate("/login");
      }, 1000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <p className="brand">WORKSPHERE HRMS</p>
        <h1>Create account</h1>

        <label htmlFor="register-username">Username</label>
        <input
          id="register-username"
          value={form.username}
          onChange={(e) =>
            setForm({ ...form, username: e.target.value })
          }
          required
        />

        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          type="email"
          value={form.email}
          onChange={(e) =>
            setForm({ ...form, email: e.target.value })
          }
          required
        />

        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          value={form.password}
          onChange={(e) =>
            setForm({ ...form, password: e.target.value })
          }
          required
        />

        {error && <p className="error">{error}</p>}
        {message && <p className="success">{message}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create account"}
        </button>

        <p className="muted">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </main>
  );
}

// ---------------- MAIN APPLICATION ----------------

function Shell({ user, onLogout }) {
  const [page, setPage] = useState("Overview");
  const [summary, setSummary] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [leaves, setLeaves] = useState([]);
  const [payroll, setPayroll] = useState([]);

const [payrollForm, setPayrollForm] = useState({
  employee_id: "",
  month: new Date().toISOString().slice(0, 7),
  basic_salary: "",
  deductions: "0",
});

const [payrollMessage, setPayrollMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [leaveForm, setLeaveForm] = useState({
    start_date: "",
    end_date: "",
    reason: "",
  });

  const [leaveMessage, setLeaveMessage] = useState("");

  // Dashboard

  async function loadDashboard() {
    try {
      const response = await api.get("/dashboard/summary");
      setSummary(response.data || {});
      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Employees

  async function loadEmployees() {
    try {
      const response = await api.get("/employees");
      const data = response.data;

      setEmployees(
        Array.isArray(data)
          ? data
          : data?.items || data?.employees || []
      );

      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function addEmployee(e) {
    e.preventDefault();

    const formElement = e.currentTarget;
    const form = new FormData(formElement);

    const employee = {
      user_id: null,
      full_name: String(form.get("name") || "").trim(),
      email: String(form.get("email") || "").trim(),
      designation: String(form.get("position") || "").trim(),
      department: String(form.get("department") || "").trim(),
      joining_date: new Date().toISOString().slice(0, 10),
      salary: 30000,
      status: "ACTIVE",
    };

    setError("");

    try {
      await api.post("/employees", employee);
      window.alert("Employee added successfully!");
      formElement.reset();
      await loadEmployees();
    } catch (err) {
      console.error("Add employee error:", err.response?.data || err);
      setError(getErrorMessage(err));
    }
  }

  async function deleteEmployee(id) {
    if (!window.confirm("Delete this employee?")) return;

    try {
      await api.delete(`/employees/${id}`);
      await loadEmployees();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Attendance

  async function loadAttendance() {
    try {
      const response = await api.get("/attendance/me");
      const data = response.data;

      const records = Array.isArray(data)
        ? data
        : data?.items || data?.records || [];

      setAttendance(records);
      setError("");
    } catch (err) {
      console.error("Failed to load attendance:", err);
      setError(getErrorMessage(err));
    }
  }

  async function checkIn() {
    setBusy(true);
    setError("");

    try {
      await api.post("/attendance/check-in");
      await loadAttendance();
      setPage("Attendance");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function checkOut() {
    setBusy(true);
    setError("");

    try {
      await api.post("/attendance/check-out");
      await loadAttendance();
      setPage("Attendance");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  // Leaves

  async function loadLeaves() {
    try {
      const response = await api.get("/leaves");
      const data = response.data;

      setLeaves(
        Array.isArray(data)
          ? data
          : data?.items || data?.leaves || []
      );

      setLeaveMessage("");
    } catch (err) {
      setLeaveMessage(getErrorMessage(err));
    }
  }

  
async function loadPayroll() {
  try {
    const response = await api.get("/payroll");
    const data = response.data;

    setPayroll(
      Array.isArray(data)
        ? data
        : data?.items || data?.payroll || []
    );

    setPayrollMessage("");
  } catch (err) {
    setPayrollMessage(getErrorMessage(err));
  }
}


async function addPayroll(e) {
  e.preventDefault();
  setPayrollMessage("");

  try {
    const params = new URLSearchParams({
      employee_id: payrollForm.employee_id,
      month: payrollForm.month,
      basic_salary: payrollForm.basic_salary,
      deductions: payrollForm.deductions || "0",
    });

    await api.post(`/payroll?${params.toString()}`);

    setPayrollMessage("Payroll record created successfully.");

    setPayrollForm({
      employee_id: "",
      month: new Date().toISOString().slice(0, 7),
      basic_salary: "",
      deductions: "0",
    });

    await loadPayroll();
  } catch (err) {
    setPayrollMessage(getErrorMessage(err));
  }
}

async function updatePayrollStatus(id, status) {
  try {
    await api.put(
      `/payroll/${id}/status?status=${encodeURIComponent(status)}`
    );

    setPayrollMessage(`Payment status updated to ${status}.`);

    await loadPayroll();
  } catch (err) {
    setPayrollMessage(getErrorMessage(err));
  }
}




async function applyLeave(e) {
  e.preventDefault();
  setLeaveMessage("");

  try {
    await api.post("/leaves", {
      start_date: leaveForm.start_date,
      end_date: leaveForm.end_date,
      reason: leaveForm.reason,
      policy_id: Number(leaveForm.policy_id),
    });

    setLeaveMessage("Leave application submitted successfully.");

    setLeaveForm({
      start_date: "",
      end_date: "",
      reason: "",
      policy_id: "",
    });

    await loadLeaves();
  } catch (err) {
    setLeaveMessage(getErrorMessage(err));
  }
}


  async function updateLeaveStatus(id, status) {
    try {
      await api.put(
        `/leaves/${id}/status?status=${encodeURIComponent(status)}`
      );

      setLeaveMessage(
        `Leave ${status.toLowerCase()} successfully.`
      );

      await loadLeaves();
    } catch (err) {
      setLeaveMessage(getErrorMessage(err));
    }
  }

  // Notifications

  async function loadNotifications() {
    try {
      const response = await api.get("/notifications");
      const data = response.data;

      setNotifications(
        Array.isArray(data) ? data : data?.items || []
      );

      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function markNotificationRead(id) {
    try {
      await api.patch(`/notifications/${id}/read`);

      setNotifications((previous) =>
        previous.map((item) =>
          item.id === id ? { ...item, is_read: true } : item
        )
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Page navigation

  useEffect(() => {
    loadDashboard();
  }, []);

  async function openPage(name) {
    setPage(name);
    setError("");

    if (name === "Overview") await loadDashboard();
    if (name === "Employees") await loadEmployees();
    if (name === "Attendance") await loadAttendance();
    if (name === "Notifications") await loadNotifications();
    if (name === "Leaves") await loadLeaves();
    if (name === "Payroll") await loadPayroll();
  }

  const stats = summary || {};
  const role = String(user?.role || "").toUpperCase();
  const canApproveLeaves = ["ADMIN", "HR"].includes(role);

  // Application layout

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h2>▣ WorkSphere</h2>
        <p className="sidebar-caption">HUMAN RESOURCES</p>

        {[
          "Overview",
          "Employees",
          "Attendance",
          "Leaves",
          "Payroll",
          "Notifications",
        ].map((name) => (
          <button
            key={name}
            className={
              page === name ? "nav-item active" : "nav-item"
            }
            onClick={() => openPage(name)}
          >
            {name}

            {name === "Notifications" &&
              notifications.some((item) => !item.is_read) && (
                <span className="notification-count">
                  {notifications.filter((item) => !item.is_read).length}
                </span>
              )}
          </button>
        ))}

        <div className="sidebar-bottom">
          <p>{user?.username || user?.name || "Employee"}</p>
          <button className="nav-item" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="muted">WorkSphere HRMS</p>
            <h1>{page}</h1>
          </div>

          <span>
            Welcome, {user?.username || user?.name || "Employee"}
          </span>
        </header>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}

        {/* OVERVIEW */}

        {page === "Overview" && (
  <>
    <section className="stats-grid">
      {[
        ["Total Employees", stats.total_employees ?? 0],
        ["Present Today", stats.present_today ?? 0],
        ["Pending Leaves", stats.pending_leaves ?? 0],
        ["Departments", stats.departments ?? stats.total_departments ?? 0],
      ].map(([label, value]) => (
        <article className="stat-card" key={label}>
          <h3>{label}</h3>
          <p>{value}</p>
        </article>
      ))}
    </section>

    <section className="panel">
      <h2>Welcome to WorkSphere</h2>
      <p>Manage employee information and record your attendance from this dashboard.</p>

      <button onClick={() => setPage("Employees")}>
        View employees
      </button>

      <button onClick={() => setPage("Attendance")}>
        My attendance
      </button>

      <button onClick={() => setPage("Notifications")}>
        View notifications
      </button>
    </section>
  </>
)}

        {/* EMPLOYEES */}

        {page === "Employees" && (
          <>
            <section className="panel">
              <h2>Add Employee</h2>

              <form className="employee-form" onSubmit={addEmployee}>
                <input
                  name="name"
                  placeholder="Employee name"
                  required
                />
                <input
                  name="email"
                  type="email"
                  placeholder="Email"
                  required
                />
                <input
                  name="department"
                  placeholder="Department"
                  required
                />
                <input
                  name="position"
                  placeholder="Position"
                  required
                />
                <button type="submit">Add employee</button>
              </form>
            </section>

            <section className="panel">
              <div className="notification-heading">
                <h2>Employee Directory</h2>
                <button
                  className="secondary-button"
                  onClick={loadEmployees}
                >
                  Refresh
                </button>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Department</th>
                      <th>Position</th>
                      <th>Action</th>
                    </tr>
                  </thead>

                  <tbody>
                    {employees.map((employee) => (
                      <tr key={employee.id}>
                        <td>{employee.id}</td>
                        <td>
                          {employee.full_name ||
                            employee.name ||
                            employee.username ||
                            "-"}
                        </td>
                        <td>
                          {employee.email ?? employee.user?.email ?? "-"}
                        </td>
                        <td>{employee.department || "-"}</td>
                        <td>
                          {employee.designation || employee.position || "-"}
                        </td>
                        <td>
                          <button
                            className="danger-button"
                            onClick={() => deleteEmployee(employee.id)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}

                    {employees.length === 0 && (
                      <tr>
                        <td colSpan="6">No employees found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {/* ATTENDANCE */}

        {page === "Attendance" && (
          <>
            <section className="panel">
              <h2>Today's Attendance</h2>
              <p className="muted">Record your working hours.</p>

              <div className="button-row">
                <button disabled={busy} onClick={checkIn}>
                  Check In
                </button>
                <button disabled={busy} onClick={checkOut}>
                  Check Out
                </button>
                <button
                  className="secondary-button"
                  onClick={loadAttendance}
                >
                  Refresh
                </button>
              </div>
            </section>

            <section className="panel">
              <h2>Attendance History</h2>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Check In</th>
                      <th>Check Out</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {attendance.map((record, index) => (
                      <tr key={record.id || index}>
                        <td>
                          {record.date || record.attendance_date || "-"}
                        </td>
                        <td>{record.check_in || record.checkIn || "-"}</td>
                        <td>{record.check_out || record.checkOut || "-"}</td>
                        <td>{record.status || "-"}</td>
                      </tr>
                    ))}

                    {attendance.length === 0 && (
                      <tr>
                        <td colSpan="4">
                          No attendance records found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {/* LEAVES */}

        {page === "Leaves" && (
          <>
            <section className="panel">
              <h2>Apply for Leave</h2>

              {leaveMessage && (
                <p
                  className={
                    leaveMessage.toLowerCase().includes("success")
                      ? "success"
                      : "error"
                  }
                >
                  {leaveMessage}
                </p>
              )}

              <form className="employee-form" onSubmit={applyLeave}>
                <label>
                  Start date
                  <input
                    type="date"
                    value={leaveForm.start_date}
                    onChange={(e) =>
                      setLeaveForm({
                        ...leaveForm,
                        start_date: e.target.value,
                      })
                    }
                    required
                  />
                </label>

                <label>
                  End date
                  <input
                    type="date"
                    min={leaveForm.start_date}
                    value={leaveForm.end_date}
                    onChange={(e) =>
                      setLeaveForm({
                        ...leaveForm,
                        end_date: e.target.value,
                      })
                    }
                    required
                  />
                </label>

                <input
                  placeholder="Reason for leave"
                  value={leaveForm.reason}
                  onChange={(e) =>
                    setLeaveForm({
                      ...leaveForm,
                      reason: e.target.value,
                    })
                  }
                  required
                />

                <button type="submit">Submit Leave</button>
              </form>
            </section>

            <section className="panel">
              <div className="notification-heading">
                <h2>Leave Requests</h2>
                <button
                  className="secondary-button"
                  onClick={loadLeaves}
                >
                  Refresh
                </button>
              </div>

              {leaveMessage && (
                <p
                  className={
                    leaveMessage.toLowerCase().includes("success")
                      ? "success"
                      : "error"
                  }
                >
                  {leaveMessage}
                </p>
              )}

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Employee ID</th>
                      <th>Start</th>
                      <th>End</th>
                      <th>Reason</th>
                      <th>Status</th>
                      {canApproveLeaves && <th>Actions</th>}
                    </tr>
                  </thead>

                  <tbody>
                    {leaves.map((leave) => (
                      <tr key={leave.id}>
                        <td>{leave.id}</td>
                        <td>{leave.employee_id ?? leave.user_id ?? "-"}</td>
                        <td>{leave.start_date || "-"}</td>
                        <td>{leave.end_date || "-"}</td>
                        <td>{leave.reason || "-"}</td>
                        <td>{leave.status || "-"}</td>

                        {canApproveLeaves && (
                          <td>
                            {String(leave.status).toUpperCase() ===
                              "PENDING" && (
                              <>
                                <button
                                  onClick={() =>
                                    updateLeaveStatus(
                                      leave.id,
                                      "APPROVED"
                                    )
                                  }
                                >
                                  Approve
                                </button>{" "}
                                <button
                                  className="danger-button"
                                  onClick={() =>
                                    updateLeaveStatus(
                                      leave.id,
                                      "REJECTED"
                                    )
                                  }
                                >
                                  Reject
                                </button>
                              </>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}

                    {leaves.length === 0 && (
                      <tr>
                        <td colSpan={canApproveLeaves ? 7 : 6}>
                          No leave requests found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {/* PAYROLL */}

        
{page === "Payroll" && (
  <>
    <section className="panel">
      <h2>Create Payroll Record</h2>

      {payrollMessage && (
        <p
          className={
            payrollMessage.toLowerCase().includes("success")
              ? "success"
              : "error"
          }
        >
          {payrollMessage}
        </p>
      )}

      <form className="employee-form" onSubmit={addPayroll}>
        <input
          type="number"
          min="1"
          placeholder="Employee ID"
          value={payrollForm.employee_id}
          onChange={(e) =>
            setPayrollForm({
              ...payrollForm,
              employee_id: e.target.value,
            })
          }
          required
        />

        <label>
          Payroll month
          <input
            type="month"
            value={payrollForm.month}
            onChange={(e) =>
              setPayrollForm({
                ...payrollForm,
                month: e.target.value,
              })
            }
            required
          />
        </label>

        <input
          type="number"
          min="0"
          step="0.01"
          placeholder="Basic salary"
          value={payrollForm.basic_salary}
          onChange={(e) =>
            setPayrollForm({
              ...payrollForm,
              basic_salary: e.target.value,
            })
          }
          required
        />

        <input
          type="number"
          min="0"
          step="0.01"
          placeholder="Deductions"
          value={payrollForm.deductions}
          onChange={(e) =>
            setPayrollForm({
              ...payrollForm,
              deductions: e.target.value,
            })
          }
          required
        />

        <button type="submit">Create Payroll</button>
      </form>
    </section>

    <section className="panel">
      <div className="notification-heading">
        <h2>Payroll Records</h2>
        <button
          className="secondary-button"
          onClick={loadPayroll}
        >
          Refresh
        </button>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Employee ID</th>
              <th>Month</th>
              <th>Basic Salary</th>
              <th>Deductions</th>
              <th>Net Salary</th>
              <th>Payment Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {payroll.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.employee_id}</td>
                <td>{item.month}</td>
                <td>{item.basic_salary}</td>
                <td>{item.deductions}</td>
                <td>{item.net_salary}</td>
                <td>{item.payment_status}</td>
                <td>
                  {String(item.payment_status).toUpperCase() !==
                    "PAID" && (
                    <button
                      onClick={() =>
                        updatePayrollStatus(item.id, "PAID")
                      }
                    >
                      Mark Paid
                    </button>
                  )}
                </td>
              </tr>
            ))}

            {payroll.length === 0 && (
              <tr>
                <td colSpan="8">No payroll records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  </>
)}


        {/* NOTIFICATIONS */}

        {page === "Notifications" && (
          <section className="panel">
            <div className="notification-heading">
              <h2>Notifications</h2>
              <button
                className="secondary-button"
                onClick={loadNotifications}
              >
                Refresh
              </button>
            </div>

            {notifications.length === 0 ? (
              <p className="muted">No notifications found.</p>
            ) : (
              <ul>
                {notifications.map((item) => (
                  <li key={item.id}>
                    <strong>{item.title}</strong>
                    <p>{item.message}</p>

                    {item.is_read ? (
                      <span className="muted">Read</span>
                    ) : (
                      <button
                        onClick={() => markNotificationRead(item.id)}
                      >
                        Mark as read
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

// ---------------- APP ENTRY ----------------

function App() {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem("worksphere_user") || "null"
      );
    } catch {
      return null;
    }
  });

  function handleLogin(userData) {
    const currentUser = userData || { username: "Employee" };

    setUser(currentUser);

    localStorage.setItem(
      "worksphere_user",
      JSON.stringify(currentUser)
    );
  }

  function handleLogout() {
    localStorage.removeItem("worksphere_token");
    localStorage.removeItem("worksphere_user");
    setUser(null);
  }

  const authenticated = Boolean(
    localStorage.getItem("worksphere_token")
  );

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            authenticated ? (
              <Navigate to="/" replace />
            ) : (
              <Login onLogin={handleLogin} />
            )
          }
        />

        <Route
          path="/register"
          element={
            authenticated ? (
              <Navigate to="/" replace />
            ) : (
              <Register />
            )
          }
        />

        <Route
          path="/*"
          element={
            authenticated ? (
              <Shell user={user} onLogout={handleLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
