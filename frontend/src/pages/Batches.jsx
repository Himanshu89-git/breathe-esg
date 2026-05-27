import { useEffect, useState } from 'react'
import { emissions } from '../services/api'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle, CheckCircle, Clock, XCircle } from 'lucide-react'

const STATUS_ICON = {
  done: <CheckCircle size={14} color="#34d399" />,
  failed: <XCircle size={14} color="#f87171" />,
  processing: <Clock size={14} color="#60a5fa" />,
  pending: <Clock size={14} color="#94a3b8" />,
}

const SOURCE_COLOR = { sap: '#f59e0b', utility: '#60a5fa', travel: '#10b981' }
const fmt = n => n == null ? '—' : Number(n).toLocaleString('en-IN')

export default function Batches() {
  const [batches, setBatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [filter, setFilter] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await emissions.batches()
      setBatches(data.results || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const shown = filter ? batches.filter(b => b.source_type === filter) : batches

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Batch History</h1>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>All ingestion sessions — provenance log for audit</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <select value={filter} onChange={e => setFilter(e.target.value)} style={{ width: 160 }}>
            <option value="">All sources</option>
            <option value="sap">SAP</option>
            <option value="utility">Utility</option>
            <option value="travel">Travel</option>
          </select>
          <button className="btn btn-secondary" onClick={load}><RefreshCw size={14} /></button>
        </div>
      </div>

      {loading ? (
        <div style={{ color: 'var(--muted)', padding: 40, textAlign: 'center' }}>Loading batches…</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {shown.map(b => (
            <div key={b.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
              {/* Header row */}
              <div
                style={{ padding: '14px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14 }}
                onClick={() => setExpanded(expanded === b.id ? null : b.id)}>

                <div style={{ flexShrink: 0 }}>{STATUS_ICON[b.status]}</div>

                <span className="badge" style={{
                  background: `${SOURCE_COLOR[b.source_type]}22`,
                  color: SOURCE_COLOR[b.source_type],
                  flexShrink: 0,
                }}>
                  {b.source_type}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 2 }}>
                    {b.file_name || 'Unnamed batch'}
                  </div>
                  {b.notes && (
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>{b.notes}</div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 20, flexShrink: 0, fontSize: 12 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>ROWS</div>
                    <div style={{ fontWeight: 600 }}>{fmt(b.row_count)}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>ERRORS</div>
                    <div style={{ fontWeight: 600, color: b.error_count > 0 ? 'var(--danger)' : 'var(--muted)' }}>{fmt(b.error_count)}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>WARNINGS</div>
                    <div style={{ fontWeight: 600, color: b.warning_count > 0 ? 'var(--warn)' : 'var(--muted)' }}>{fmt(b.warning_count)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>INGESTED</div>
                    <div style={{ fontSize: 12 }}>{new Date(b.created_at).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })}</div>
                  </div>
                </div>

                <div style={{ color: 'var(--muted)', fontSize: 16, flexShrink: 0 }}>
                  {expanded === b.id ? '▲' : '▼'}
                </div>
              </div>

              {/* Expanded detail */}
              {expanded === b.id && (
                <div style={{ borderTop: '1px solid var(--border)', padding: '16px 20px', background: 'var(--surface2)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 16, fontSize: 12 }}>
                    {[
                      ['Batch ID', b.id.slice(0, 8) + '…'],
                      ['Uploaded by', b.uploaded_by?.username || '—'],
                      ['Period start', b.reporting_period_start || '—'],
                      ['Period end', b.reporting_period_end || '—'],
                    ].map(([k, v]) => (
                      <div key={k}>
                        <div style={{ color: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-mono)',
                          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{k}</div>
                        <div className="mono">{v}</div>
                      </div>
                    ))}
                  </div>

                  {b.error_log?.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--font-mono)',
                        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                        Parse log ({b.error_log.length} entries)
                      </div>
                      <div style={{ background: 'var(--surface)', borderRadius: 6, padding: 12,
                        maxHeight: 180, overflow: 'auto' }}>
                        {b.error_log.slice(0, 30).map((e, i) => (
                          <div key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)',
                            color: e.type === 'warning' ? 'var(--warn)' : 'var(--danger)',
                            marginBottom: 3, lineHeight: 1.5 }}>
                            {e.type === 'warning' ? '⚠ ' : '✗ '}
                            Row {e.row}: {e.error || e.warning}
                          </div>
                        ))}
                        {b.error_log.length > 30 && (
                          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
                            …and {b.error_log.length - 30} more
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: 14 }}>
                    <Link to={`/records?batch=${b.id}`} className="btn btn-secondary btn-sm"
                      style={{ textDecoration: 'none', display: 'inline-flex' }}>
                      View records from this batch →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          ))}

          {!shown.length && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--muted)', padding: 48 }}>
              No batches yet. <Link to="/upload" style={{ color: 'var(--accent)' }}>Upload your first file →</Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
