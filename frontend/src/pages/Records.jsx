import { useEffect, useState, useCallback } from 'react'
import { emissions } from '../services/api'
import { CheckCircle, XCircle, Flag, AlertTriangle, ChevronDown, ChevronUp, Eye, RefreshCw } from 'lucide-react'

const fmt = n => n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })
const fmtCo2 = n => n == null ? '—' : n >= 1000 ? `${(n/1000).toFixed(2)} t` : `${Number(n).toFixed(2)} kg`

const STATUS_BADGE = {
  pending: 'badge-pending',
  approved: 'badge-approved',
  rejected: 'badge-rejected',
  flagged: 'badge-flagged',
}

const SCOPE_COLOR = { '1': '#f87171', '2': '#60a5fa', '3': '#a78bfa' }

function ReviewModal({ record, onClose, onDone }) {
  const [action, setAction] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!action) return
    setLoading(true)
    try {
      await emissions.review(record.id, action, notes)
      onDone()
      onClose()
    } catch (e) {
      alert('Review failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }} onClick={onClose}>
      <div className="card fade-in" style={{ width: 520, maxHeight: '85vh', overflow: 'auto' }}
        onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Review Record</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 18 }}>×</button>
        </div>

        {/* Record detail */}
        <div style={{ background: 'var(--surface2)', borderRadius: 8, padding: 14, marginBottom: 16, fontSize: 13 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              ['Category', record.category],
              ['Scope', `Scope ${record.scope}`],
              ['Source', record.source_type],
              ['Date', record.activity_date],
              ['Quantity', `${fmt(record.quantity)} ${record.unit}`],
              ['CO₂e', record.kg_co2e ? `${fmtCo2(record.kg_co2e)} CO₂e` : '—'],
              ['Facility', record.facility || '—'],
              ['Cost Center', record.cost_center || '—'],
            ].map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{k}</div>
                <div style={{ fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>

          {record.is_suspicious && (
            <div style={{ marginTop: 12, background: '#3b1f00', borderRadius: 6, padding: '8px 12px',
              display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <AlertTriangle size={14} color="#fb923c" style={{ flexShrink: 0, marginTop: 1 }} />
              <span style={{ fontSize: 12, color: '#fb923c' }}>{record.suspicion_reason}</span>
            </div>
          )}
        </div>

        {/* Raw data */}
        <details style={{ marginBottom: 16 }}>
          <summary style={{ fontSize: 12, color: 'var(--muted)', cursor: 'pointer', marginBottom: 6 }}>
            View raw source data
          </summary>
          <pre style={{ background: 'var(--surface2)', borderRadius: 6, padding: 12, fontSize: 10,
            fontFamily: 'var(--font-mono)', color: 'var(--muted)', overflow: 'auto', maxHeight: 160 }}>
            {JSON.stringify(record.raw_data, null, 2)}
          </pre>
        </details>

        {/* Action buttons */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ marginBottom: 8 }}>Action</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { id: 'approve', label: 'Approve', cls: 'btn-primary' },
              { id: 'flag', label: 'Flag', cls: 'btn-warn' },
              { id: 'reject', label: 'Reject', cls: 'btn-danger' },
            ].map(a => (
              <button key={a.id}
                className={`btn ${action === a.id ? a.cls : 'btn-secondary'}`}
                onClick={() => setAction(a.id)}>
                {a.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <label>Notes (optional)</label>
          <textarea rows={2} value={notes} onChange={e => setNotes(e.target.value)}
            placeholder="Add context for this review decision…" />
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={!action || loading} onClick={submit}>
            {loading ? 'Saving…' : 'Confirm →'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Records() {
  const [records, setRecords] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ scope: '', status: '', source_type: '', is_suspicious: '' })
  const [selected, setSelected] = useState(new Set())
  const [reviewing, setReviewing] = useState(null)
  const [bulkLoading, setBulkLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '')) }
      const { data } = await emissions.records(params)
      setRecords(data.results || [])
      setCount(data.count || 0)
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => { load() }, [load])

  const toggleSelect = id => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === records.length) setSelected(new Set())
    else setSelected(new Set(records.map(r => r.id)))
  }

  const bulkApprove = async () => {
    setBulkLoading(true)
    try {
      await emissions.bulkApprove([...selected])
      setSelected(new Set())
      load()
    } finally {
      setBulkLoading(false)
    }
  }

  const filterEl = (key, label, opts) => (
    <div>
      <label style={{ marginBottom: 4 }}>{label}</label>
      <select value={filters[key]} onChange={e => { setFilters(p => ({...p, [key]: e.target.value})); setPage(1) }}>
        <option value="">All</option>
        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  )

  const totalPages = Math.ceil(count / 50)

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Review Records</h1>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>{count} records total</p>
        </div>
        <button className="btn btn-secondary" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20, padding: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {filterEl('scope', 'Scope', [['1','Scope 1 — Direct'],['2','Scope 2 — Electricity'],['3','Scope 3 — Travel']])}
          {filterEl('status', 'Status', [['pending','Pending'],['approved','Approved'],['flagged','Flagged'],['rejected','Rejected']])}
          {filterEl('source_type', 'Source', [['sap','SAP'],['utility','Utility'],['travel','Travel']])}
          {filterEl('is_suspicious', 'Suspicious', [['true','Suspicious only']])}
        </div>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div style={{ background: '#1a2332', border: '1px solid var(--border)', borderRadius: 8,
          padding: '10px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>{selected.size} selected</span>
          <button className="btn btn-primary btn-sm" onClick={bulkApprove} disabled={bulkLoading}>
            <CheckCircle size={13} />
            {bulkLoading ? 'Approving…' : `Approve ${selected.size}`}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => setSelected(new Set())}>
            Clear
          </button>
        </div>
      )}

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>Loading records…</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 36 }}>
                    <input type="checkbox" checked={selected.size === records.length && records.length > 0}
                      onChange={toggleAll} style={{ width: 'auto', cursor: 'pointer' }} />
                  </th>
                  <th>Scope</th>
                  <th>Category</th>
                  <th>Source</th>
                  <th>Date</th>
                  <th>Quantity</th>
                  <th>CO₂e</th>
                  <th>Facility</th>
                  <th>Status</th>
                  <th>Flags</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {records.map(r => (
                  <tr key={r.id} style={{ opacity: r.status === 'rejected' ? 0.5 : 1 }}>
                    <td>
                      <input type="checkbox" checked={selected.has(r.id)}
                        onChange={() => toggleSelect(r.id)} style={{ width: 'auto', cursor: 'pointer' }} />
                    </td>
                    <td>
                      <span style={{ color: SCOPE_COLOR[r.scope], fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                        S{r.scope}
                      </span>
                    </td>
                    <td style={{ fontWeight: 500 }}>{r.category?.replace('_', ' ')}</td>
                    <td><span className={`badge badge-${r.source_type === 'sap' ? 'pending' : r.source_type === 'utility' ? 'approved' : 'flagged'}`}>{r.source_type}</span></td>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>{r.activity_date}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{fmt(r.quantity)} <span style={{ color: 'var(--muted)', fontSize: 10 }}>{r.unit}</span></td>
                    <td className="mono" style={{ fontSize: 12 }}>{fmtCo2(r.kg_co2e)} <span style={{ color: 'var(--muted)', fontSize: 10 }}>CO₂e</span></td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>{r.facility || '—'}</td>
                    <td><span className={`badge ${STATUS_BADGE[r.status]}`}>{r.status}</span></td>
                    <td>
                      {r.is_suspicious && (
                        <span title={r.suspicion_reason}>
                          <AlertTriangle size={14} color="#fb923c" />
                        </span>
                      )}
                    </td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => setReviewing(r)}>
                        <Eye size={12} /> Review
                      </button>
                    </td>
                  </tr>
                ))}
                {!records.length && (
                  <tr><td colSpan={11} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>
                    No records match these filters.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, padding: 16, borderTop: '1px solid var(--border)' }}>
            <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
            <span style={{ fontSize: 12, color: 'var(--muted)', alignSelf: 'center' }}>Page {page} of {totalPages}</span>
            <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
          </div>
        )}
      </div>

      {reviewing && (
        <ReviewModal record={reviewing} onClose={() => setReviewing(null)} onDone={load} />
      )}
    </div>
  )
}
