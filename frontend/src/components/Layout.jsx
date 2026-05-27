import { NavLink, Outlet } from 'react-router-dom'
import { Wind, LayoutDashboard, Upload, Table2, History, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload Data' },
  { to: '/records', icon: Table2, label: 'Review Records' },
  { to: '/batches', icon: History, label: 'Batch History' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, flexShrink: 0,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        padding: '20px 0',
        position: 'fixed', top: 0, bottom: 0, left: 0, zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ padding: '0 20px 24px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              background: 'linear-gradient(135deg, #10b981, #3b82f6)',
              borderRadius: 8, padding: '6px', display: 'flex',
            }}>
              <Wind size={16} color="white" />
            </div>
            <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: '-0.02em' }}>Breathe ESG</span>
          </div>
          {user?.tenant && (
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
              {user.tenant.name}
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '16px 10px' }}>
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 7, marginBottom: 2,
                fontSize: 13, fontWeight: 500, textDecoration: 'none',
                color: isActive ? 'var(--accent)' : 'var(--muted)',
                background: isActive ? 'rgba(16,185,129,0.1)' : 'transparent',
                transition: 'all 0.15s',
              })}>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div style={{ padding: '16px 10px', borderTop: '1px solid var(--border)' }}>
          <div style={{ padding: '8px 12px', marginBottom: 4 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>
              {user?.first_name} {user?.last_name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
              {user?.role}
            </div>
          </div>
          <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }}
            onClick={logout}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ marginLeft: 220, flex: 1, padding: '32px 32px', minHeight: '100vh' }}>
        <Outlet />
      </main>
    </div>
  )
}
