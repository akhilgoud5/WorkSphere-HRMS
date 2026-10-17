import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom'
import { Users, CalendarCheck, CalendarDays, Wallet, Bell, LayoutDashboard, LogOut, BriefcaseBusiness } from 'lucide-react'
import api from './api'

function Login({ onLogin }) {
  const [registerMode, setRegisterMode] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const change = e => setForm({ ...form, [e.target.name]: e.target.value })
  async function submit(e) {
    e.preventDefault(); setError('')
    try {
      if (registerMode) {
        await api.post('/auth/register', form)
      }
      const response = await api.post('/auth/login', { username: form.username, password: form.password })
      localStorage.setItem('worksphere_token', response.data.access_token)
      localStorage.setItem('worksphere_user', JSON.stringify(response.data.user))
      onLogin(response.data.user); navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not connect. Check that the backend is running.')
    }
  }
  return <main className="login-wrap"><form className="login-card" onSubmit={submit}>
    <div className="brand-mark"><BriefcaseBusiness size={28}/></div>
    <p className="eyebrow">WORKSPHERE HRMS</p><h1>{registerMode ? 'Create your account' : 'Welcome back'}</h1>
    <p className="muted">Your workplace, organized in one place.</p>
    <label>Username<input name="username" value={form.username} onChange={change} minLength="3" required /></label>
    {registerMode && <label>Email<input type="email" name="email" value={form.email} onChange={change} required /></label>}
    <label>Password<input type="password" name="password" value={form.password} onChange={change} minLength="8" required /></label>
    {error && <p className="error">{error}</p>}
    <button className="primary full" type="submit">{registerMode ? 'Register & continue' : 'Sign in'}</button>
    <p className="switch-text">{registerMode ? 'Already have an account?' : 'New to WorkSphere?'} <button type="button" className="text-button" onClick={() => {setRegisterMode(!registerMode);setError('')}}>{registerMode ? 'Sign in' : 'Create account'}</button></p>
    <p className="hint">Public registration creates an EMPLOYEE account. HR/Admin accounts must be assigned securely by an administrator.</p>
  </form></main>
}

const navItems = [
  ['Overview', '/', LayoutDashboard], ['Employees', '/employees', Users],
  ['Attendance', '/attendance', CalendarCheck], ['Leaves', '/leaves', CalendarDays],
  ['Payroll', '/payroll', Wallet], ['Notifications', '/notifications', Bell]
]
function Shell({ user, onLogout, children }) {
  return <div className="app-shell"><aside className="sidebar">
    <div className="sidebar-brand"><span className="brand-mark small"><BriefcaseBusiness size={20}/></span><span>WorkSphere<small>HR MANAGEMENT</small></span></div>
    <p className="nav-caption">WORKSPACE</p><nav>{navItems.map(([label, path, Icon]) => <Link key={path} to={path} className={location.pathname === path ? 'nav-link active' : 'nav-link'}><Icon size={18}/>{label}</Link>)}</nav>
    <div className="sidebar-bottom"><div className="avatar">{user?.username?.slice(0,1).toUpperCase()}</div><div className="user-label"><strong>{user?.username}</strong><small>{user?.role}</small></div><button className="icon-button" title="Sign out" onClick={onLogout}><LogOut size={18}/></button></div>
  </aside><main className="main-area"><header className="topbar"><div><span className="muted">Workspace</span><span className="crumb"> / HR Management</span></div><div className="top-user"><span className="status-dot"></span> Signed in as {user?.role}</div></header>{children}</main></div>
}
function Overview({ user }) {
  const [summary, setSummary] = useState(null)
  const [message, setMessage] = useState('')
  useEffect(() => { api.get('/dashboard/summary').then(r => setSummary(r.data)).catch(e => setMessage(e.response?.status === 403 ? 'Dashboard analytics are available to HR and Admin accounts.' : 'Connect to the backend to load live statistics.')) }, [])
  const cards = [
    { label: 'Total employees', value: summary?.total_employees ?? '—', icon: Users, tone: 'blue' },
    { label: 'Active employees', value: summary?.active_employees ?? '—', icon: BriefcaseBusiness, tone: 'green' },
    { label: 'Inactive employees', value: summary?.inactive_employees ?? '—', icon: CalendarCheck, tone: 'orange' },
    { label: 'Departments', value: summary?.departments ?? '—', icon: LayoutDashboard, tone: 'purple' }
  ]
  return <div className="page"><div className="page-heading"><div><p className="eyebrow">OVERVIEW</p><h1>Good to see you, {user?.username} 👋</h1><p className="muted">Here's what's happening across your workplace.</p></div><span className="role-pill">{user?.role}</span></div>
    {message && <div className="notice">{message}</div>}
    <div className="stats-grid">{cards.map(({label,value,icon:Icon,tone})=><article className="stat-card" key={label}><div className={`stat-icon ${tone}`}><Icon size={21}/></div><p>{label}</p><strong>{value}</strong><span className="stat-foot">Live system data</span></article>)}</div>
    <div className="content-grid"><section className="panel"><div className="panel-title"><div><h2>HR operations</h2><p className="muted">Core areas of the HRMS</p></div><span className="live-label">● Workspace</span></div><div className="operation-list">
      {[['Employee directory','Manage employee profiles and departments',Users,'/employees'],['Attendance tracking','Review check-ins and work hours',CalendarCheck,'/attendance'],['Leave requests','Apply for and track time off',CalendarDays,'/leaves'],['Payroll records','View salary and payroll information',Wallet,'/payroll']].map(([title,desc,Icon,path])=><Link to={path} className="operation" key={title}><span className="operation-icon"><Icon size={20}/></span><span className="operation-text"><strong>{title}</strong><small>{desc}</small></span><span className="arrow">→</span></Link>)}
    </div></section><section className="panel welcome-panel"><div className="welcome-art"><div className="art-circle"><Users size={42}/></div><span className="art-dot one"></span><span className="art-dot two"></span></div><p className="eyebrow">ONE CONNECTED WORKPLACE</p><h2>People first. Work simpler.</h2><p className="muted">Keep employee information, attendance, leave, and payroll workflows organized in one place.</p><div className="progress-row"><span>Project setup</span><strong>Starter version</strong></div><div className="progress-bar"><span></span></div></section></div>
  </div>
}

function Employees() {
  const [items, setItems] = useState([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    full_name: '',
    designation: '',
    department: '',
    joining_date: '',
    salary: '',
    status: 'ACTIVE',
    user_id: ''
  })

  async function load() {
    try {
      const r = await api.get('/employees', { params: { search } })
      setItems(r.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load employees.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  function resetForm() {
    setEditingId(null)
    setForm({
      full_name: '',
      designation: '',
      department: '',
      joining_date: '',
      salary: '',
      status: 'ACTIVE',
      user_id: ''
    })
  }

  function change(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  function editEmployee(employee) {
    setEditingId(employee.id)
    setForm({
      full_name: employee.full_name || '',
      designation: employee.designation || '',
      department: employee.department || '',
      joining_date: employee.joining_date?.slice(0, 10) || '',
      salary: employee.salary ?? '',
      status: employee.status || 'ACTIVE',
      user_id: employee.user_id ?? ''
    })
    setMessage('')
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function saveEmployee(e) {
    e.preventDefault()
    setError('')
    setMessage('')

    const payload = {
      full_name: form.full_name.trim(),
      designation: form.designation.trim(),
      department: form.department.trim(),
      joining_date: form.joining_date,
      salary: Number(form.salary),
      status: form.status,
      user_id: form.user_id === '' ? null : Number(form.user_id)
    }

    try {
      if (editingId !== null) {
        await api.put(`/employees/${editingId}`, payload)
        setMessage('Employee updated successfully.')
      } else {
        await api.post('/employees', payload)
        setMessage('Employee created successfully.')
      }
      resetForm()
      await load()
    } catch (e) {
      setError(
        e.response?.data?.detail ||
        'Could not save employee. Check your HR/Admin role and required fields.'
      )
    }
  }

  async function deleteEmployee(id) {
    if (!window.confirm('Are you sure you want to delete this employee?')) return

    setError('')
    setMessage('')
    try {
      await api.delete(`/employees/${id}`)
      setMessage('Employee deleted successfully.')
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not delete employee.')
    }
  }

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">PEOPLE</p>
          <h1>Employee directory</h1>
          <p className="muted">Search, add, update, and manage employee records.</p>
        </div>
      </div>

      <section className="panel">
        <h2>{editingId !== null ? 'Edit employee' : 'Add employee'}</h2>

        <form className="employee-form" onSubmit={saveEmployee}>
          <label>
            Full name
            <input name="full_name" value={form.full_name} onChange={change} required />
          </label>

          <label>
            Designation
            <input name="designation" value={form.designation} onChange={change} required />
          </label>

          <label>
            Department
            <input name="department" value={form.department} onChange={change} required />
          </label>

          <label>
            Joining date
            <input type="date" name="joining_date" value={form.joining_date} onChange={change} required />
          </label>

          <label>
            Salary
            <input type="number" min="0" step="0.01" name="salary" value={form.salary} onChange={change} required />
          </label>

          <label>
            Status
            <select name="status" value={form.status} onChange={change}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </label>

          <label>
            Linked user ID (optional)
            <input type="number" min="1" name="user_id" value={form.user_id} onChange={change} />
          </label>

          <div className="form-actions">
            <button className="primary" type="submit">
              {editingId !== null ? 'Save changes' : 'Add employee'}
            </button>
            {editingId !== null && (
              <button type="button" onClick={resetForm}>Cancel edit</button>
            )}
          </div>
        </form>

        {message && <p className="success-message">{message}</p>}
        {error && <p className="error">{typeof error === 'string' ? error : JSON.stringify(error)}</p>}
      </section>

      <section className="panel">
        <h2>Employee directory</h2>
        <div className="table-toolbar">
          <input
            placeholder="Search employee name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
          />
          <button className="primary" onClick={load}>Search</button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Designation</th>
                <th>Department</th>
                <th>Joining date</th>
                <th>Salary</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(employee => (
                <tr key={employee.id}>
                  <td>
                    <strong>{employee.full_name}</strong>
                    <small className="cell-sub">Employee #{employee.id}</small>
                  </td>
                  <td>{employee.designation || '—'}</td>
                  <td>{employee.department || '—'}</td>
                  <td>{employee.joining_date?.slice(0, 10) || '—'}</td>
                  <td>{employee.salary ?? '—'}</td>
                  <td><span className="status-pill">{employee.status}</span></td>
                  <td>
                    <button type="button" onClick={() => editEmployee(employee)}>Edit</button>{' '}
                    <button type="button" onClick={() => deleteEmployee(employee.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!items.length && !error && <p className="empty">No employee records yet.</p>}
        </div>
      </section>
    </div>
  )
}

function Placeholder({title,description}) { return <div className="page"><p className="eyebrow">WORKSPACE MODULE</p><h1>{title}</h1><p className="muted">{description}</p><section className="panel coming"><div className="stat-icon blue"><BriefcaseBusiness size={24}/></div><h2>Module scaffold ready</h2><p className="muted">This page is prepared. We'll implement its database tables, API endpoints, and working UI in the next steps.</p></section></div> }
export default function App() {
  const [user,setUser] = useState(()=>{try{return JSON.parse(localStorage.getItem('worksphere_user'))}catch{return null}})
  function logout(){localStorage.removeItem('worksphere_token');localStorage.removeItem('worksphere_user');setUser(null)}
  if(!user) return <Login onLogin={setUser}/>
  return <Shell user={user} onLogout={logout}><Routes>
    <Route path="/" element={<Overview user={user}/>}/>
    <Route path="/employees" element={<Employees/>}/>
    <Route path="/attendance" element={<Placeholder title="Attendance" description="Track employee check-in and check-out times."/>}/>
    <Route path="/leaves" element={<Placeholder title="Leave management" description="Submit leave requests and review their status."/>}/>
    <Route path="/payroll" element={<Placeholder title="Payroll" description="Manage payroll periods, salary calculations, and payslips."/>}/>
    <Route path="/notifications" element={<Placeholder title="Notifications" description="View updates about leave, attendance, and payroll."/>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes></Shell>
}
