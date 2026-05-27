import { useEffect, useState } from 'react'
import { emissions } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { AlertTriangle, CheckCircle, Clock, XCircle, Flag, Leaf, Zap, Plane } from 'lucide-react'
import { Link } from 'react-router-dom'

const fmt = n => n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 1 })
const fmtCo2 = n => n >= 1000 ? `${(n/1000).toFixed(2)} tCO₂e` : `${Number(n).toFixed(1)} kgCO₂e`

const SCOPE_COLORS = { scope_1: '#f87171', scope_2: '#60a5fa', scope_3: '#a78bfa' }
const SOURCE_COLORS = { sap: '#f59e0b', utility: '#60a5fa', travel: '#10b981' }

function StatCard({ icon: Icon, label, value, sub, color = 'var(--accent)' }) {
  return (
    <div className="card" style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      <div style={{
        background: `${color}22`, borderRadius: 8, padding: 10, flexShrink: 0,
      }}>
        <Icon size={20} color={color} />
      </div>
      <div>
        <div style={{ color: 'var(--muted)', fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 24, fontWeight: 600, lineHeight: 1 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    emissions.stats().then(r => setStats(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading dashboard…</div>
  if (!stats) return null

  const scopeData = Object.entries(stats.by_scope || {}).map(([k, v]) => ({
    name: `Scope ${k.split('_')[1]}`,
    kg_co2e: v.kg_co2e,
    count: v.count,
  }))

  const sourceData = Object.entries(stats.by_source || {}).map(([k, v]) => ({
    name: k.toUpperCase(),
    kg_co2e: v.kg_co2e,
  }))

  const reviewData = [
    { name: 'Pending', value: stats.pending, color: '#60a5fa' },
    { name: 'Approved', value: stats.approved, color: '#34d399' },
    { name: 'Flagged', value: stats.flagged, color: '#fbbf24' },
    { name: 'Rejected', value: stats.rejected, color: '#f87171' },
  ].filter(d => d.value > 0)

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Emissions Dashboard</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>Overview of ingested activity data across all sources</p>
      </div>

      {/* Stat row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <StatCard icon={Leaf} label="Total CO₂e" value={fmtCo2(stats.total_kg_co2e)} sub={`${fmt(stats.total_records)} records`} color="#10b981" />
        <StatCard icon={Clock} label="Pending Review" value={fmt(stats.pending)} sub="awaiting analyst sign-off" color="#60a5fa" />
        <StatCard icon={AlertTriangle} label="Suspicious" value={fmt(stats.suspicious)} sub="flagged for attention" color="#f59e0b" />
        <StatCard icon={CheckCircle} label="Approved" value={fmt(stats.approved)} sub="locked for audit" color="#34d399" />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Scope breakdown */}
        <div className="card">
          <h3 style={{ fontSize: 13, fontWeight: 500, marginBottom: 16, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>
            Emissions by Scope
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={scopeData} barSize={28}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                formatter={v => [fmtCo2(v), 'CO₂e']}
              />
              <Bar dataKey="kg_co2e" radius={[4,4,0,0]}>
                {scopeData.map((_, i) => (
                  <Cell key={i} fill={Object.values(SCOPE_COLORS)[i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
            {scopeData.map((s, i) => (
              <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: Object.values(SCOPE_COLORS)[i] }} />
                <span style={{ color: 'var(--muted)' }}>{s.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Source breakdown */}
        <div className="card">
          <h3 style={{ fontSize: 13, fontWeight: 500, marginBottom: 16, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>
            Emissions by Source
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sourceData} barSize={28}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                formatter={v => [fmtCo2(v), 'CO₂e']}
              />
              <Bar dataKey="kg_co2e" radius={[4,4,0,0]}>
                {sourceData.map((s, i) => (
                  <Cell key={i} fill={Object.values(SOURCE_COLORS)[i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Review status pie */}
        <div className="card">
          <h3 style={{ fontSize: 13, fontWeight: 500, marginBottom: 16, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>
            Review Status
          </h3>
          <ResponsiveContainer width="100%" height={130}>
            <PieChart>
              <Pie data={reviewData} dataKey="value" cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={3}>
                {reviewData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
            {reviewData.map(d => (
              <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                <span style={{ color: 'var(--muted)' }}>{d.name}: {d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent batches */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 13, fontWeight: 500, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>
            Recent Ingestion Batches
          </h3>
          <Link to="/batches" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>View all →</Link>
        </div>
        <table>
          <thead>
            <tr>
              <th>Source</th><th>File</th><th>Rows</th><th>Errors</th><th>Status</th><th>Date</th>
            </tr>
          </thead>
          <tbody>
            {(stats.recent_batches || []).map(b => (
              <tr key={b.id}>
                <td><span className={`badge badge-${b.source_type === 'sap' ? 'pending' : b.source_type === 'utility' ? 'approved' : 'flagged'}`}>{b.source_type}</span></td>
                <td className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{b.file_name || '—'}</td>
                <td>{fmt(b.row_count)}</td>
                <td style={{ color: b.error_count > 0 ? 'var(--danger)' : 'var(--muted)' }}>{b.error_count}</td>
                <td><span className={`badge badge-${b.status === 'done' ? 'approved' : b.status === 'failed' ? 'rejected' : 'pending'}`}>{b.status}</span></td>
                <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(b.created_at).toLocaleDateString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!stats.recent_batches?.length && (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '24px', fontSize: 13 }}>
            No batches yet. <Link to="/upload" style={{ color: 'var(--accent)' }}>Upload data →</Link>
          </div>
        )}
      </div>
    </div>
  )
}
